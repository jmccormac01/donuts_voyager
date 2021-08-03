"""
Test script for guiding Voyager with donuts
"""
import glob
import os
import sys
import socket as s
import traceback
import time
import threading
import logging
import queue
import json
import uuid
import signal
from shutil import copyfile
from collections import defaultdict
import numpy as np
from astropy.io import fits
from donuts import Donuts
import voyager_utils as vutils
import voyager_db as vdb
from PID import PID

# TODO: Add RemoteActionAbort call when things go horribly wrong

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=logging-fstring-interpolation
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-nested-blocks
# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=broad-except

# set this when ctrl+c happens, then exit cleanly
EXIT_EVENT = threading.Event()


class DonutsStatus:
    """
    Current status of Donuts guiding
    """
    CALIBRATING, GUIDING, IDLE, UNKNOWN = np.arange(4)


class Message:
    """
    Define some dicts for specific Voyager two way commands

    Also define some flags to compare responses from Voyager's
    RemoteActionResult ActionResultInt to.
    """
    NEED_INIT = 0
    READY = 1
    RUNNING = 2
    PAUSE = 3
    OK = 4
    FINISHED_ERROR = 5
    ABORTING = 6
    ABORTED = 7
    TIMEOUT = 8
    TIME_END = 9
    OK_PARTIAL = 10

    @staticmethod
    def pulse_guide(uid, idd, direction, duration):
        """
        Create a message object for pulse guiding

        Also return the response code that says things
        went well. Typically 4

        Parameters
        ----------
        uid : string
            unique ID for this command
        idd : int
            unique ID for this command
        direction : dict
            X and Y directional information for a correction
        duration : dict
            X and Y pulse guide durations for a correction

        Returns
        -------
        message : dict
            JSON dumps ready dict for a pulse guide command

        Raises
        ------
        None
        """
        message = {"method": "RemotePulseGuide",
                   "params": {"UID": uid,
                              "Direction": direction,
                              "Duration": duration,
                              "Parallelized": "true"},
                   "id": idd}
        return message

    @staticmethod
    def camera_shot(uid, idd, exptime, save_file, filename):
        """
        Create a message object for taking an image
        with the CCD camera

        Also return the response code that says things
        went well. Typically 4

        Parameters
        ----------
        uid : string
            unique ID for this command
        idd : int
            unique ID for this command
        exptime : int
            exposure time of the image to be taken
        save_file : boolean
            flag to save the file or not
        filename : string
            path to the file for saving

        Returns
        -------
        message : dict
            JSON dumps ready dict for a pulse guide command

        Raises
        ------
        None
        """
        message = {"method": "RemoteCameraShot",
                   "params": {"UID": uid,
                              "Expo": exptime,
                              "Bin": 1,
                              "IsROI": "false",
                              "ROITYPE": 0,
                              "ROIX": 0,
                              "ROIY": 0,
                              "ROIDX": 0,
                              "ROIDY": 0,
                              "FilterIndex": 0,
                              "ExpoType": 0,
                              "SpeedIndex": 0,
                              "ReadoutIndex": 0,
                              "IsSaveFile": str(save_file).lower(),
                              "FitFileName": filename,
                              "Gain": 1,
                              "Offset": 0,
                              "Parallelized": "true"},
                   "id": idd}
        return message

    @staticmethod
    def goto_radec(uid, idd, ra, dec):
        """
        Create a message object for repointing the telescope

        Parameters
        ----------
        uid : string
            unique ID for this command
        idd : int
            unique ID for this command
        ra : string
            RA of the target field (HH MM SS.ss)
        dec : string
            DEC of the target field (DD MM SS.ss)

        Returns
        -------
        message : dict
            JSON dumps ready dict for a pulse guide command

        Raises
        ------
        None
        """
        message = {"method": "RemotePrecisePointTarget",
                   "params": {"UID": uid,
                              "IsText": "true",
                              "RA": 0,
                              "DEC": 0,
                              "RAText": ra,
                              "DECText": dec,
                              "Parallelized": "true"},
                   "id": idd}
        return message


class Response:
    """
    Keep track of outstanding responses from Voyager
    """

    def __init__(self, uid, idd, ok_status):
        """
        Initialise response object

        Parameters
        ----------
        uid : string
            unique ID for this command
        idd : int
            unique ID for this command
        ok_status : int
            command return value that we search for
            to ensure everything went ok. Any other
            value means there was an error
        """
        self.uid = uid
        self.idd = idd
        self.uid_recv = False
        self.idd_recv = False
        self.uid_status = None
        self.idd_status = None
        self.ok_status = ok_status

    def uid_received(self, status):
        """
        Update uuid response as received

        Parameters
        ----------
        status : int
            response code to command for given uid

        Returns
        -------
        None

        Raises
        ------
        None
        """
        self.uid_recv = True
        self.uid_status = status

    def idd_received(self, status):
        """
        Update uuid response as received

        Parameters
        ----------
        status : int
            response code to command for given idd

        Returns
        -------

        Raises
        ------
        None
        """
        self.idd_recv = True
        self.idd_status = status

    def all_ok(self):
        """
        Check if uid and idd are all ok
        Return True if so and False if not

        idd is left hardcoded to 0
        uid code is supplied on init

        Parameters
        ----------

        Returns
        -------
        all_ok : boolean
            Did we get a good response for the command submitted?
            True of False

        Raises
        ------
        None
        """
        return self.uid_recv and self.idd_recv and \
            self.uid_status == self.ok_status and self.idd_status == 0


class Voyager:
    """
    Voyager interaction class
    """

    def __init__(self, cfg):
        """
        Initialise the Voyager autoguiding class instance

        Parameters
        ----------
        cfg : dict
            Configuration information
        """
        self.socket = None
        self.socket_ip = cfg['socket_ip']
        self.socket_port = cfg['socket_port']
        self.host = cfg['host']
        self.inst = 1
        self.image_extension = cfg['image_extension']

        # Fits image path keyword
        self._voyager_path_keyword = "FITPathAndName"
        self._INFO_SIGNALS = ["Polling", "Version", "Signal", "NewFITReady"]

        # set up important image header keywords
        self.filter_keyword = cfg['filter_keyword']
        self.field_keyword = cfg['field_keyword']
        self.ra_keyword = cfg['ra_keyword']
        self.dec_keyword = cfg['dec_keyword']
        self.xbin_keyword = cfg['xbin_keyword']
        self.ybin_keyword = cfg['ybin_keyword']
        self.ra_axis = cfg['ra_axis']
        self._declination = None

        # keep track of current status
        self._status = DonutsStatus.UNKNOWN

        # add a message object for sharing between methods
        self._msg = Message()

        # some internal tracking variables
        self._image_id = 0
        self._comms_id = 0
        self._last_poll_time = None

        # set up the guiding thread
        self._latest_guide_frame = None
        self._guide_condition = threading.Condition()

        # set up a queue to send back results from guide_loop
        self._results_queue = queue.Queue(maxsize=1)

        # set up some root directory info for host and container
        self.calibration_root = cfg['calibration_root']
        self.reference_root = cfg['reference_root']
        self.data_root = cfg['data_root']
        self.calibration_root_host = cfg['calibration_root_host']
        self.reference_root_host = cfg['reference_root_host']
        self.data_root_host = cfg['data_root_host']

        # this calibration directory inside calibration root gets made if we calibrate
        self._calibration_dir = None
        self.calibration_step_size_ms = cfg['calibration_step_size_ms']
        self.calibration_n_iterations = cfg['calibration_n_iterations']
        self.calibration_exptime = cfg['calibration_exptime']

        # set up objects to hold calibration info
        self._direction_store = None
        self._scale_store = None

        # add some places to keep track of reference images change overs
        self._ref_file = None
        self._last_field = None
        self._last_filter = None
        self._last_xbin = None
        self._last_ybin = None
        self._donuts_ref = None

        # set up the PID loop coeffs etc
        self.pid_x_p = cfg["pid_coeffs"]["x"]["p"]
        self.pid_x_i = cfg["pid_coeffs"]["x"]["i"]
        self.pid_x_d = cfg["pid_coeffs"]["x"]["d"]
        self.pid_x_setpoint = cfg["pid_coeffs"]["set_x"]

        self.pid_y_p = cfg["pid_coeffs"]["y"]["p"]
        self.pid_y_i = cfg["pid_coeffs"]["y"]["i"]
        self.pid_y_d = cfg["pid_coeffs"]["y"]["d"]
        self.pid_y_setpoint = cfg["pid_coeffs"]["set_y"]

        # placeholders for actual PID objects
        self._pid_x = None
        self._pid_y = None

        # ag correction buffers - used for outlier rejection
        self.guide_buffer_length = cfg["guide_buffer_length"]
        self.guide_buffer_sigma = cfg["guide_buffer_sigma"]
        self._buff_x = None
        self._buff_y = None
        self._buff_x_sigma = None
        self._buff_y_sigma = None

        # set up max error in pixels
        self.max_error_pixels = cfg['max_error_pixels']

        # set up stabilisation
        self._stabilised = False
        # set up how many attempts to stabilise are allowed
        self.n_images_to_stabilise = cfg['n_images_to_stabilise']
        # initialise stabilisation counter
        self._images_to_stabilise = self.n_images_to_stabilise

        # calibrated pixels to time ratios and the directions
        self.pixels_to_time = cfg['pixels_to_time']
        self.guide_directions = cfg['guide_directions']

        # initialise all the things
        self.__initialise_guide_buffer()

        # start with the guider unstabilised
        self.__initialise_pid_loop(stabilised=False)

        # some donuts algorithm config
        self.donuts_subtract_bkg = cfg['donuts_subtract_bkg']

    def __resolve_host_path(self, data_type, path):
        """
        Take in a path from Voyager which is absolute on
        the container. We need a path to the volume on the
        host instead.

        Data are mounted to self.data_root_host
        Refs are mounted to self.reference_root_host
        Donuts calibs are mounted to self.calibration_root_host
        Logs are mounted to self.logging_root_host

        Parameters
        ----------
        data_type : string
            which type of data are we working with?
            data, calib or references?
        path : string
            host path to image

        Returns
        -------
        cont_path : string
            host path as seen from inside the container

        Raises
        ------
        None
        """
        # fetch the image name form the full path
        filename = path.split('/')[-1]

        # get tonight, break path on this string
        nght = vutils.get_tonight()

        if data_type == "data":
            cont_root = self.data_root_host
            cont_path = f"{cont_root}\\{nght}\\{filename}"
        elif data_type == "calib":
            cont_root = self.calibration_root_host
            cont_path = f"{cont_root}\\{nght}\\{filename}"
        else:
            cont_root = self.reference_root_host
            cont_path = f"{cont_root}\\{filename}"

        return cont_path

    def __resolve_container_path(self, data_type, path):
        """
        Take in a path from Voyager which is absolute on
        the host machine. We need a path to the volume inside
        the Docker container.

        Data are mounted to self.data_root
        Refs are mounted to self.reference_root
        Donuts calibs are mounted to self.calibration_root
        Logs are mounted to self.logging_root

        Parameters
        ----------
        data_type : string
            which type of data are we working with?
            data, calib or references?
        path : string
            host path to image

        Returns
        -------
        cont_path : string
            host path as seen from inside the container

        Raises
        ------
        None
        """
        # fetch the image name form the full path
        filename = path.split('\\')[-1]

        # get tonight, break path on this string
        nght = vutils.get_tonight()

        if data_type == "data":
            cont_root = self.data_root
            cont_path = f"{cont_root}/{nght}/{filename}"
        elif data_type == "calib":
            cont_root = self.calibration_root
            cont_path = f"{cont_root}/{nght}/{filename}"
        else:
            cont_root = self.reference_root
            cont_path = f"{cont_root}/{filename}"

        return cont_path

    def run(self):
        """
        Open a connection and maintain it with Voyager.
        Listen to autoguiding and calibration jobs.
        Dispatch them and continue listening until
        told to abort.

        Parameters
        ----------

        Returns
        -------
        None

        Raises
        ------
        None
        """
        # spawn the guide calculation thread
        guide_thread = threading.Thread(target=self.__guide_loop)
        guide_thread.daemon = True
        guide_thread.start()

        # open the socket to Voyager
        self.__open_socket()

        # keep it alive and listen for jobs
        self.__keep_socket_alive()

        # set guiding statuse to IDLE
        self._status = DonutsStatus.IDLE

        # loop until told to stop
        while 1:
            # end on ctrl+c
            if EXIT_EVENT.set():
                break

            # listen for a response or a new job to do
            rec = self.__receive()

            # was there a command? If so, do something, else, do nothing/keep alive
            if rec:

                # handle events
                if 'Event' in rec.keys():

                    # do nothing for events that just give us some info
                    if rec['Event'] in self._INFO_SIGNALS:
                        logging.debug(f"RECEIVED: {rec}")

                    # handle the autoguider calibration event
                    elif rec['Event'] == "DonutsCalibrationRequired":
                        # send a dummy command with a small delay for now
                        self._status = DonutsStatus.CALIBRATING
                        self.__send_donuts_message_to_voyager("DonutsCalibrationStart")

                        # run the calibration process
                        self.__calibrate_donuts()

                        # send the calibration done message
                        self.__send_donuts_message_to_voyager("DonutsCalibrationDone")
                        self._status = DonutsStatus.IDLE

                    # handle the autoguiding event
                    elif rec['Event'] == "DonutsRecenterRequired":
                        logging.debug(f"RECEIVED: {rec}")
                        # if guider is IDLE, do stuff, otherwise do nothing
                        if self._status == DonutsStatus.IDLE:
                            # set the current mode to guiding
                            self._status = DonutsStatus.GUIDING
                            # send a DonutsRecenterStart reply
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")

                            # make a containerised version of the file path and
                            # keep a local copy of the image to guide on's path
                            host_path = rec[self._voyager_path_keyword]
                            last_image = self.__resolve_container_path("data", host_path)

                            # set the latest image and notify the guide loop thread to wake up
                            with self._guide_condition:
                                self._latest_guide_frame = last_image
                                self._guide_condition.notify()

                            # fetch the results from the queue
                            direction, duration = self._results_queue.get()

                            # only try guiding if a valid correction was returned, otherwise, do nothing
                            if duration['x'] != 0 or duration['y'] != 0:
                                logging.info(
                                    f"CORRECTION: {direction['x']}:{duration['x']} {direction['y']}:{duration['y']}")

                                # send a pulseGuide command followed by a loop for responses
                                # this must be done before the next command can be sent
                                # if both are sent ok, we send the DonutsRecenterDone, otherwise we send an error
                                try:
                                    # make x correction message
                                    uuid_x = str(uuid.uuid4())
                                    message_x = self._msg.pulse_guide(uuid_x, self._comms_id, direction['x'],
                                                                      duration['x'])
                                    # send x correction
                                    self.__send_two_way_message_to_voyager(message_x)
                                    self._comms_id += 1

                                    # make y correction message
                                    uuid_y = str(uuid.uuid4())
                                    message_y = self._msg.pulse_guide(uuid_y, self._comms_id, direction['y'],
                                                                      duration['y'])
                                    # send the y correction
                                    self.__send_two_way_message_to_voyager(message_y)
                                    self._comms_id += 1

                                    # send a DonutsRecenterDone message
                                    self.__send_donuts_message_to_voyager("DonutsRecenterDone")
                                except Exception as e:
                                    # send a recentering error
                                    print(e)
                                    self.__send_donuts_message_to_voyager("DonutsRecenterError",
                                                                          f"Failed to PulseGuide {last_image}")
                                    traceback.print_exc()
                            else:
                                logging.info(
                                    f"No guide correction returned for {last_image}, skipping and sending "
                                    f"DonutsRecenterDone...")
                                # send a DonutsRecenterDone message
                                self.__send_donuts_message_to_voyager("DonutsRecenterDone")

                            # set the current mode back to IDLE
                            self._status = DonutsStatus.IDLE

                        # ignore commands if we're already doing something
                        else:
                            logging.warning("Donuts is busy, skipping...")
                            # send Voyager a start and a done command to keep it happy
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")
                            self.__send_donuts_message_to_voyager("DonutsRecenterDone")

                    # handle the abort event
                    elif rec['Event'] == "DonutsAbort":
                        logging.info(f"RECEIVED: {rec}")
                        logging.info("EVENT: Donuts abort requested, dying peacefully")
                        # close the socket
                        self.__close_socket()
                        # exit
                        sys.exit(0)

                    # erm, something has gone wrong
                    else:
                        logging.error('Oh dear, something unforseen has occurred. Here\'s what...')
                        logging.error(f"Failed parsing {rec}")

            # do we need to poll again?
            now = time.time()
            time_since_last_poll = now - self._last_poll_time
            if time_since_last_poll > 5:
                # ping the keep alive
                self.__keep_socket_alive()

    @staticmethod
    def __dec_str_to_deg(declination):
        """
        Convert DD MM SS.ss into DD.dddd
        """
        deg, mins, sec = declination.split(' ')
        if deg[0] == '-':
            return int(deg) - float(mins) / 60. - float(sec) / 3600.
        else:
            return int(deg) + float(mins) / 60. + float(sec) / 3600.

    def __guide_loop(self):
        """
        Analyse incoming images for guiding offsets.
        Results are communicated to the main run thread
        using the results_queue

        Parameters
        ----------

        Returns
        -------
        None

        Raises
        ------
        None
        """

        while 1:
            # end on ctrl+c
            if EXIT_EVENT.set():
                break
            # block until a frame is available for processing
            with self._guide_condition:
                while self._latest_guide_frame is None:
                    self._guide_condition.wait()

                last_image = self._latest_guide_frame

                # check if we're still observing the same field
                # pylint: disable=no-member
                with fits.open(last_image) as ff:
                    # current field and filter?
                    current_filter = ff[0].header[self.filter_keyword]
                    current_field = ff[0].header[self.field_keyword]
                    current_xbin = ff[0].header[self.xbin_keyword]
                    current_ybin = ff[0].header[self.ybin_keyword]
                    declination = ff[0].header[self.dec_keyword]
                    self._declination = self.__dec_str_to_deg(declination)
                # pylint: enable=no-member

                # if something changes or we haven't started yet, sort out a reference image
                if current_field != self._last_field or current_filter != self._last_filter or \
                        current_xbin != self._last_xbin or current_ybin != self._last_ybin or self._donuts_ref is None:
                    # reset PID loop to unstabilised state
                    self.__initialise_pid_loop(stabilised=False)
                    # reset the guide buffer
                    self.__initialise_guide_buffer()
                    # reset stabilised flag
                    self._stabilised = False

                    # replacement block using database
                    # look for a reference image for this field, filter, binx and biny
                    self._ref_file = vdb.get_reference_image_path(current_field, current_filter,
                                                                  current_xbin, current_ybin)

                    # if we have a reference, use it. Otherwise store this image as the new reference frame
                    if self._ref_file is not None:
                        do_correction = True
                    else:
                        # set the last image as reference
                        self._ref_file = last_image
                        ref_filename = self._ref_file.split('/')[-1]
                        # copy it to the special storage area
                        copyfile(self._ref_file, f"{self.reference_root}/{ref_filename}")
                        # set thw copied image to the reference in the database
                        vdb.set_reference_image(self._ref_file, current_field, current_filter,
                                                current_xbin, current_ybin)
                        # set skip correction as new reference was just defined as this current image
                        do_correction = False

                    # make this image the reference, update the last field/filter also
                    self._donuts_ref = Donuts(self._ref_file, subtract_bkg=self.donuts_subtract_bkg)
                else:
                    do_correction = True

                # update the last field/filter values
                self._last_field = current_field
                self._last_filter = current_filter
                self._last_xbin = current_xbin
                self._last_ybin = current_ybin

                # do the correction if required
                if do_correction:
                    # work out shift here
                    shift = self._donuts_ref.measure_shift(last_image)
                    logging.info(f"Raw shift measured: x:{shift.x.value:.2f} y:{shift.y.value:.2f}")

                    # process the shifts and add the results to the queue
                    direction, duration = self.__process_guide_correction(shift)

                    # add the post-PID values to the results queue
                    self._results_queue.put((direction, duration))

                else:
                    # return a null correction and do nothing
                    direction = {"x": self.guide_directions["+x"],
                                 "y": self.guide_directions["+y"]}
                    duration = {"x": 0, "y": 0}
                    self._results_queue.put((direction, duration))

                # set this to None for the next image
                self._latest_guide_frame = None

    def __open_socket(self):
        """
        Open a socket connection to Voyager

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.socket.settimeout(1.0)
        try:
            self.socket.connect((self.socket_ip, self.socket_port))
        except s.error:
            logging.fatal('Voyager socket connect failed!')
            logging.fatal('Check the application interface is running!')
            traceback.print_exc()
            sys.exit(1)

    def __close_socket(self):
        """
        Close the socket once finished

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        self.socket.close()

    def __send(self, message, n_attempts=3):
        """
        Low level message sending method. Note no listening
        is done here.

        Parameters
        ----------
        message : string
            message to communicate to Voyager
        n_attempts: int, optional
            default = 3
            max number of tries to send, before giving up

        Returns
        -------
        sent : boolean
            Did the message send ok?
            True or False

        Raises
        ------
        None
        """
        sent = False
        while not sent and n_attempts > 0:
            n_attempts -= 1
            try:
                # send the command
                self.socket.sendall(bytes(message, encoding='utf-8'))
                sent = True
                # update the last poll time
                self._last_poll_time = time.time()
                logging.debug(f"SENT: {message.rstrip()}")
            except Exception as e:
                print(e)
                logging.error(f"CANNOT SEND {message} TO VOYAGER [{n_attempts}]")
                traceback.print_exc()
                sent = False

        return sent

    def __receive(self, n_bytes=1024):
        """
        Receive a message of n_bytes in length from Voyager

        Parameters
        ----------
        n_bytes : int, optional
            Number of bytes to read from socket
            default = 1024

        Returns
        -------
        message : dict
            json parsed response from Voyager

        Raises
        ------
        None
        """
        try:
            message = json.loads(self.socket.recv(n_bytes))
        except s.timeout:
            message = {}
        return message

    def __keep_socket_alive(self):
        """
        Convenience method to keep socket open.
        Voyager's internal polling is reset upon
        receipt of this message

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        now = str(time.time())
        polling = {"Event": "Polling",
                   "Timestamp": now,
                   "Host": self.host,
                   "Inst": self.inst}

        # send the polling string
        polling_str = json.dumps(polling) + "\r\n"
        _ = self.__send(polling_str)

    @staticmethod
    def __parse_jsonrpc(response):
        """
        Take a jsonrpc response and figure out
        what happened. If there is an error result is
        missing and error object is there instead

        Parameters
        ----------
        response : dict
            jsonrpc response from Voyager

        Returns
        -------
        rec_idd : int
            response_id, used to match async commands/responses
        result : int
            result code, 0 = ok, all else = not ok
        error_code : int
            used to determine type of error
        error_msg : string
            description of any error

        Raises
        ------
        None
        """
        # get the response ID
        rec_idd = response['id']

        try:
            result = response['result']
            error_code = None
            error_msg = None
        except KeyError:
            result = -1
            error_code = response['error']['code']
            error_msg = response['error']['message']

        return rec_idd, result, error_code, error_msg

    @staticmethod
    def __parse_remote_action_result(response):
        """
        Take a remote action result and see what happened

        Parameters
        ----------
        response : dict
            Voyager RemoteActionResult response

        Returns
        -------
        uid : string
            unique id for the corresponding command
        result : int
            result code, 4 = ok, all else = not ok
        motivo : string
            description of any error
        param_ret : dict
            parameters returned by command

        Raises
        ------
        None
        """
        result = response['ActionResultInt']
        uid = response['UID']
        motivo = response['Motivo']
        param_ret = response['ParamRet']
        return uid, result, motivo, param_ret

    def __send_donuts_message_to_voyager(self, event, error=None):
        """
        Acknowledge a command from Voyager

        Parameters
        ----------
        event : string
            name of event to send to Voyager
        error : string, optional
            description of donuts error
            default = None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        now = str(time.time())
        message = {"Event": event,
                   "Timestamp": now,
                   "Host": self.host,
                   "Inst": self.inst}
        if error is not None:
            message['DonutsError'] = error

        # send the command
        msg_str = json.dumps(message) + "\r\n"
        _ = self.__send(msg_str)

    def __send_abort_message_to_voyager(self, uid, idd):
        """
        If things go pear shaped and donuts is quitting,
        tell Voyager to abort this UID:IDD also

        Parameters
        ----------
        uid : string
            unique ID for this command
        idd : int
            unique ID for this command

        Returns
        -------
        None

        Raises
        ------
        None
        """
        message = {'method': 'RemoteActionAbort',
                   'params': {'UID': uid},
                   'id': idd}
        msg_str = json.dumps(message) + "\r\n"

        # send the command
        _ = self.__send(msg_str)

    def __send_two_way_message_to_voyager(self, message):
        """
        Issue any two way command to Voyager

        Wait for the initial jsonrpc response, act accordingly
        If all good, wait for the RemoteActionResult event, act accordingly

        The helper Message class (above) allows for easy creation
        of the message objects (dictionaries) to pass to this method

        Parameters
        ----------
        message : dict
            A message object containing the relevant json info
            for the command we want to send to Voyager

        Returns
        -------
        None

        Raises
        ------
        Exception : When unable to send message
        """
        # grab this message's UID and ID values
        uid = message['params']['UID']
        idd = message['id']

        msg_str = json.dumps(message) + "\r\n"

        # initialise an empty response class
        # add the OK status we want to see returned
        response = Response(uid, idd, self._msg.OK)

        # loop until both responses are received
        cb_loop_count = 0
        while not response.uid_recv:

            # loop until we get a valid response to issuing a command
            while not response.idd_recv:

                # try sending the message and then waiting for a response
                sent = False
                while not sent:
                    # send the command
                    sent = self.__send(msg_str)
                    if sent:
                        logging.debug(f"CALLBACK ADD: {uid}:{idd}")

                logging.debug(f"JSONRPC CALLBACK LOOP [{cb_loop_count + 1}]: {uid}:{idd}")
                rec = self.__receive()

                # handle the jsonrpc response (1 of 2 responses needed)
                if "jsonrpc" in rec.keys():
                    logging.debug(f"RECEIVED: {rec}")
                    rec_idd, result, err_code, err_msg = self.__parse_jsonrpc(rec)

                    # we only care bout IDs for the commands we just sent right now
                    if rec_idd == idd:
                        # result = 0 means OK, anything else is bad
                        # leave this jsonrpc check hardcoded
                        if result != 0:
                            logging.error(f"Problem with command id: {idd}")
                            logging.error(f"{err_code} {err_msg}")
                            # Leo said if result!=0, we have a serious issue. Therefore abort.
                            self.__send_abort_message_to_voyager(uid, idd)
                            raise Exception(f"ERROR: Could not send message {msg_str}")
                        else:
                            logging.debug(f"Command id: {idd} returned correctly")
                            # add the response if things go well. if things go badly we're quitting anyway
                            response.idd_received(result)
                    else:
                        logging.warning(f"Waiting for idd: {idd}, ignoring response for idd: {rec_idd}")

                # increment loop counter to keep track of how long we're waiting
                cb_loop_count += 1

            # if we exit the while loop above we can assume that
            # we got a jsonrpc response to the pulse guide command
            # here we start listening for it being done
            logging.debug(f"EVENT CALLBACK LOOP [{cb_loop_count + 1}]: {uid}:{idd}")
            rec = self.__receive()

            # handle the RemoteActionResult response (2 of 2 needed)
            if "Event" in rec.keys():

                if rec['Event'] == "RemoteActionResult":
                    logging.debug(f"RECEIVED: {rec}")
                    rec_uid, result, *_ = self.__parse_remote_action_result(rec)

                    # check we have a response for the thing we want
                    if rec_uid == uid:
                        # result = 4 means OK, anything else is an issue
                        if result != self._msg.OK:
                            logging.error(f"Problem with command uid: {uid}")
                            logging.error(f"{rec}")
                            # TODO: Consider adding a RemoteActionAbort here if shit hits the fan
                        else:
                            logging.debug(f"Command uid: {uid} returned correctly")
                            # add the response, regardless if it's good or bad, so we can end this loop
                            response.uid_received(result)
                    else:
                        logging.warning(f"Waiting for uid: {uid}, ignoring response for uid: {rec_uid}")

                elif rec['Event'] in self._INFO_SIGNALS:
                    logging.debug(f"RECEIVED: {rec}")

                else:
                    logging.warning(f"Unknown response {rec}")

            # no response? do nothing
            elif not rec.keys():
                pass
            else:
                logging.warning(f"Unknown response {rec}")

            # keep the connection alive while waiting
            now = time.time()
            time_since_last_poll = now - self._last_poll_time
            if time_since_last_poll > 5:
                # ping the keep alive
                self.__keep_socket_alive()

            # increment event loop counter
            cb_loop_count += 1

        # check was everything ok and raise an exception if not
        if not response.all_ok():
            raise Exception(f"ERROR: Could not send message {msg_str}")

    def __calibration_filename(self, direction, pulse_time):
        """
        Return a calibration filename

        Parameters
        ----------
        direction : string
            Direction of offset applied to this calibration image
        pulse_time : int
            Number of ms the telescope was pulse guided for
            in the direction above

        Returns
        -------
        path : string
            Filename/path to use for saving a calibration image

        Raises
        ------
        None
        """
        return f"{self._calibration_dir}/step_{self._image_id:06d}_d{direction}_{pulse_time}ms{self.image_extension}"

    @staticmethod
    def __determine_shift_direction_and_magnitude(shift):
        """
        Take a donuts shift object and work out
        the direction of the shift and the distance

        Parameters
        ----------
        shift : Donuts.shift
            A shift object containing the offset between
            two images from Donuts

        Returns
        -------
        direction : string
            The direction of the offset
        magnitude : float
            The magnitude of the shift in pixels

        Raises
        ------
        None
        """
        sx = shift.x.value
        sy = shift.y.value
        if abs(sx) > abs(sy):
            if sx > 0:
                direction = '-x'
            else:
                direction = '+x'
            magnitude = abs(sx)
        else:
            if sy > 0:
                direction = '-y'
            else:
                direction = '+y'
            magnitude = abs(sy)
        return direction, magnitude

    def __calibrate_donuts(self):
        """
        Run the calibration routine. Here we take and
        image, nudge the telescope, take another and
        repeat for the 4 directions. Then we use donuts
        to determine the shift and calibrate the pulse
        guide command.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """

        # set up objects to hold calib info
        self._direction_store = defaultdict(list)
        self._scale_store = defaultdict(list)

        # set up calibration directory
        self._calibration_dir = vutils.get_data_dir(self.calibration_root, windows=False)

        # delete old calibration files
        files = glob.glob(self._calibration_dir+"/*.FIT")
        for f in files:
            os.remove(f)

        # get the reference filename
        filename_cont = self.__calibration_filename("R", 0)
        filename_host = self.__resolve_host_path("calib", filename_cont)

        # create a command uuid
        shot_uuid = str(uuid.uuid4())

        # take an image at the current location
        try:
            message_shot = self._msg.camera_shot(shot_uuid, self._comms_id, self.calibration_exptime, True,
                                                 filename_host)
            self.__send_two_way_message_to_voyager(message_shot)
            self._comms_id += 1
            self._image_id += 1
        except Exception as e:
            print(e)
            self.__send_donuts_message_to_voyager("DonutsCalibrationError", f"Failed to take image {filename_host}")

        # make the image we took the reference image
        donuts_ref = Donuts(filename_cont, subtract_bkg=self.donuts_subtract_bkg)

        # loop over the 4 directions for the requested number of iterations
        for _ in range(self.calibration_n_iterations):
            for i in range(4):
                # pulse guide in direction i
                try:
                    uuid_i = str(uuid.uuid4())
                    message_pg = self._msg.pulse_guide(uuid_i, self._comms_id, i, self.calibration_step_size_ms)
                    # send pulse guide command in direction i
                    self.__send_two_way_message_to_voyager(message_pg)
                    self._comms_id += 1
                except Exception as e:
                    print(e)
                    # send a recentering error
                    self.__send_donuts_message_to_voyager("DonutsRecenterError",
                                                          f"Failed to PulseGuide {i} {self.calibration_step_size_ms}")
                    traceback.print_exc()

                # take an image
                try:
                    # get the filenames
                    filename_cont = self.__calibration_filename(str(i), self.calibration_step_size_ms)
                    filename_host = self.__resolve_host_path("calib", filename_cont)

                    shot_uuid = str(uuid.uuid4())
                    message_shot = self._msg.camera_shot(shot_uuid, self._comms_id, self.calibration_exptime, True,
                                                         filename_host)
                    self.__send_two_way_message_to_voyager(message_shot)
                    self._comms_id += 1
                    self._image_id += 1
                except Exception as e:
                    print(e)
                    self.__send_donuts_message_to_voyager("DonutsCalibrationError",
                                                          f"Failed to take image {filename_host}")

                # measure the offset and update the reference image
                shift = donuts_ref.measure_shift(filename_cont)
                direction, magnitude = self.__determine_shift_direction_and_magnitude(shift)
                logging.info(f"SHIFT: {direction} {magnitude}")
                self._direction_store[i].append(direction)
                self._scale_store[i].append(magnitude)
                donuts_ref = Donuts(filename_cont, subtract_bkg=self.donuts_subtract_bkg)

        # now do some analysis on the run from above
        # check that the directions are the same every time for each orientation
        for direc in self._direction_store:
            logging.info(self._direction_store[direc])
            if len(set(self._direction_store[direc])) != 1:
                logging.error(f"ERROR: PROBLEM WITH CALIBRATED DIRECTION {self._direction_store[direc]}")
            logging.info(f"{direc}: {self._direction_store[direc][0]}")
            # TODO: check
            config["guide_directions"][self._direction_store[direc][0]] = direc

        # now work out the ms/pix scales from the calbration run above
        for direc in self._scale_store:
            ratio = self.calibration_step_size_ms / np.average(self._scale_store[direc])
            logging.info(f"{direc}: {ratio:.2f} ms/pixel")
            if config["guide_directions"]["+x"] == direc:
                config["pixels_to_time"]["+x"] = ratio
            elif config["guide_directions"]["-x"] == direc:
                config["pixels_to_time"]["-x"] = ratio
            elif config["guide_directions"]["+y"] == direc:
                config["pixels_to_time"]["+y"] = ratio
            elif config["guide_directions"]["-y"] == direc:
                config["pixels_to_time"]["-y"] = ratio

        vutils.save_config(config, 'configs/config.toml')
        self.pixels_to_time = config['pixels_to_time']
        self.guide_directions = config['guide_directions']

        # print out the storage areas for reference in case some bad measurements were made
        for direc in self._direction_store:
            logging.info(f"Direction store: {direc} {self._direction_store[direc]}")
            logging.info(f"Scale store: {direc} {self._scale_store[direc]}")

    def __initialise_pid_loop(self, stabilised):
        """
        (Re)initialise the PID loop objects
        for the X and Y directions

        Parameters
        ----------
        stabilised : boolean
            Are we stabilised or not?

        Returns
        -------
        None

        Raises
        ------
        None
        """
        if stabilised:
            # initialise the PID loop with the coeffs from config
            self._pid_x = PID(self.pid_x_p, self.pid_x_i, self.pid_x_d)
            self._pid_y = PID(self.pid_y_p, self.pid_y_i, self.pid_y_d)
        else:
            # force 100% proportional during stabilisation
            self._pid_x = PID(1.0, 0.0, 0.0)
            self._pid_y = PID(1.0, 0.0, 0.0)

        # set the PID set points (typically 0)
        self._pid_x.setPoint(self.pid_x_setpoint)
        self._pid_y.setPoint(self.pid_y_setpoint)

    def __initialise_guide_buffer(self):
        """
        (Re) initialise the ag measurement buffer.

        Clears the buffer lists for a new field/filter

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        self._buff_x = []
        self._buff_y = []

    def __get_null_correction(self):
        """
        Return an empty correction

        Parameters
        ----------
        None

        Returns
        -------
        direction : dict
            Direction object for correction
        duration : dict
            Duration object for correction

        Raises
        ------
        None
        """
        direction = {"x": self.guide_directions["+x"],
                     "y": self.guide_directions["+y"]}
        duration = {"x": 0, "y": 0}
        return direction, duration

    def __truncate_correction(self, x, y):
        """
        Apply a pass filter on the corrections
        if needed.

        Parameters
        ----------
        x : float
            X correction
        y : float
            Y correction

        Returns
        -------
        xt : float
            Filtered x correction (if needed)
        yt : float
            Filtered y correction (if needed)

        Raises
        ------
        None
        """
        # filter x
        if x >= self.max_error_pixels:
            xt = self.max_error_pixels
        elif x <= -self.max_error_pixels:
            xt = -self.max_error_pixels
        else:
            xt = x

        # filter y
        if y >= self.max_error_pixels:
            yt = self.max_error_pixels
        elif y <= -self.max_error_pixels:
            yt = -self.max_error_pixels
        else:
            yt = y
        return xt, yt

    def __determine_direction_and_duration(self, x, y, cos_dec):
        """
        Take the correction in X and Y in pixels
        and convert it to a direction and duration object
        for pulse guide

        Parameters
        ----------
        x : float
            X correction
        y : float
            Y correction

        Returns
        -------
        direction : dict
            direction object for correction
        duration : dict
            duration object for correction

        Raises
        ------
        None
        """

        # determine the directions and scaled shifr magnitudes (in ms) to send
        # abs() on -ve duration otherwise throws back an error
        if 0 < x <= self.max_error_pixels:
            guide_time_x = x * self.pixels_to_time['+x']
            if self.ra_axis == 'x':
                guide_time_x = guide_time_x / cos_dec
            guide_direction_x = self.guide_directions["+x"]
        elif 0 > x >= -self.max_error_pixels:
            guide_time_x = abs(x * self.pixels_to_time['-x'])
            if self.ra_axis == 'x':
                guide_time_x = guide_time_x / cos_dec
            guide_direction_x = self.guide_directions["-x"]
        else:
            guide_time_x = 0
            guide_direction_x = self.guide_directions["+x"]

        if 0 < y <= self.max_error_pixels:
            guide_time_y = y * self.pixels_to_time['+y']
            if self.ra_axis == 'y':
                guide_time_y = guide_time_y / cos_dec
            guide_direction_y = self.guide_directions["+y"]
        elif 0 > y >= -self.max_error_pixels:
            guide_time_y = abs(y * self.pixels_to_time['-y'])
            if self.ra_axis == 'y':
                guide_time_y = guide_time_y / cos_dec
            guide_direction_y = self.guide_directions["-y"]
        else:
            guide_time_y = 0
            guide_direction_y = self.guide_directions["+y"]

        # bake these final values into the direction/duration results
        direction = {"x": guide_direction_x,
                     "y": guide_direction_y}
        duration = {"x": guide_time_x,
                    "y": guide_time_y}

        return direction, duration

    def __process_guide_correction(self, shift):
        """
        Take a Donuts shift object. Analyse the x and y
        components. Compare them to the recent history of
        corrections and reject outliers. Additionally, pass
        x and y corrections through a PID loop and trim results
        to the max allowed guide correction, if required

        Parameters
        ----------
        shift : Donuts.shift object
            Contains the X and Y offset values for a
            recently analysed image

        Returns
        -------
        direction : dict
            Correction directions to apply for X and Y
        duration : dict
            Correction pulse guide durations to apply
            for X and Y
        """
        # get x and y from shift object
        shift_x = shift.x.value
        shift_y = shift.y.value

        # handle big shifts during stabilisation and when stabilised
        if (abs(shift_x) > self.max_error_pixels or abs(shift_y) > self.max_error_pixels) and self._stabilised:
            logging.warning(f"Offset larger than max allowed shift {self.max_error_pixels}: x: {shift_x} y:{shift_y}")
            logging.warning("Skipping this correction...")

            # make a shift arguments tuple to store in the database
            shift_args = (self._ref_file, self._latest_guide_frame, self._stabilised, shift_x, shift_y,
                          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1, 1)
            # log the culled correction to the database
            vdb.log_shifts_to_db(shift_args)

            direction, duration = self.__get_null_correction()
            return direction, duration
        # if we're stabilising, limit big shifts to the max value during this phase
        elif (abs(shift_x) > self.max_error_pixels or abs(shift_y) > self.max_error_pixels) and not self._stabilised:
            # if x is too big, limit it
            pre_pid_x, pre_pid_y = self.__truncate_correction(shift_x, shift_y)
        else:
            pre_pid_x = shift_x
            pre_pid_y = shift_y

        # handle stabilisation
        if not self._stabilised and pre_pid_x < 2 and pre_pid_y < 2:
            # set flag
            self._stabilised = True
            # reset the number of images to stabilise for next time
            self._images_to_stabilise = self.n_images_to_stabilise
            # log a message
            logging.info("Stabilisation complete, reseting PID loop")
            # reset the pid loop
            self.__initialise_pid_loop(stabilised=True)
            # reset the guide buffer
            self.__initialise_guide_buffer()
        # continue trying to stabilise
        elif not self._stabilised and (pre_pid_x > 2 or pre_pid_y > 2) and self._images_to_stabilise >= 0:
            # keep forcing 100% proportional correction
            self.__initialise_pid_loop(stabilised=False)
            self._images_to_stabilise -= 1
        # check if we've been trying to stabilise for too long
        elif not self._stabilised and (pre_pid_x > 2 or pre_pid_y > 2) and self._images_to_stabilise < 0:
            logging.error(f"We've been trying to stabilise >{self.n_images_to_stabilise} images")
            logging.error("There appears to be an error, quiting donuts")
            self.__send_donuts_message_to_voyager("DonutsRecenterError", "Failed to stabilise guiding")
            sys.exit(1)
        else:
            pass

        # get telescope declination to scale RA corrections
        dec_rads = np.radians(self._declination)
        cos_dec = np.cos(dec_rads)

        # handle comparisons to the guide buffer
        # pop the earliest buffer value if > N measurements
        while len(self._buff_x) > self.guide_buffer_length:
            self._buff_x.pop(0)
        while len(self._buff_y) > self.guide_buffer_length:
            self._buff_y.pop(0)
        assert len(self._buff_x) == len(self._buff_y)

        # kill anything that is > sigma_buffer sigma buffer stats, but only after buffer is full
        # otherwise, wait to get better stats
        if len(self._buff_x) < self.guide_buffer_length and len(self._buff_y) < self.guide_buffer_length:
            logging.info("Filling AG stats buffer")
            self._buff_x_sigma = 0.0
            self._buff_y_sigma = 0.0
        else:
            self._buff_x_sigma = np.std(self._buff_x)
            self._buff_y_sigma = np.std(self._buff_y)
            if abs(pre_pid_x) > self.guide_buffer_sigma * self._buff_x_sigma or abs(
                    pre_pid_y) > self.guide_buffer_sigma * self._buff_y_sigma:
                # store the original values in the buffer, even if correction
                # was too big, this will allow small outliers to be caught
                logging.warning(f"Guide correction(s) too large x:{pre_pid_x:.2f} y:{pre_pid_y:.2f}")
                self._buff_x.append(pre_pid_x)
                self._buff_y.append(pre_pid_y)

                # make a shift arguments tuple to store in the database
                shift_args = (self._ref_file, self._latest_guide_frame, self._stabilised, shift_x, shift_y,
                              pre_pid_x, pre_pid_y, 0.0, 0.0, 0.0, 0.0, self._buff_x_sigma, self._buff_y_sigma,
                              1, 1)
                # log the culled correction to the database
                vdb.log_shifts_to_db(shift_args)

                # send back empty correction
                direction, duration = self.__get_null_correction()
                return direction, duration

        # pass corrections through the PID controller
        # update the PID controllers, run them in parallel
        post_pid_x = self._pid_x.update(pre_pid_x) * -1
        post_pid_y = self._pid_y.update(pre_pid_y) * -1
        logging.info(f"PID: x:{post_pid_x:.2f} y:{post_pid_y:.2f}")

        # check if we went over the max allowed shift
        # trim if so, do nothing otherwise
        final_x, final_y = self.__truncate_correction(post_pid_x, post_pid_y)

        logging.info(f"PID[trunc]: x:{final_x:.2f} y:{final_y:.2f}")

        # make a shift arguments tuple to store in the database
        shift_args = (self._ref_file, self._latest_guide_frame, self._stabilised, shift_x, shift_y,
                      pre_pid_x, pre_pid_y, post_pid_x, post_pid_y, final_x, final_y, self._buff_x_sigma,
                      self._buff_y_sigma, 0, 0)
        # log the culled correction to the database
        vdb.log_shifts_to_db(shift_args)

        # convert correction into direction/duration objects
        direction, duration = self.__determine_direction_and_duration(final_x, final_y, cos_dec)

        # store the original pre-pid values in the buffer
        self._buff_x.append(pre_pid_x)
        self._buff_y.append(pre_pid_y)

        return direction, duration


def signal_handler():
    """
    Handle ctrl+c
    """
    EXIT_EVENT.set()


if __name__ == "__main__":
    # handle ctrl+c
    signal.signal(signal.SIGINT, signal_handler)

    # load the config file
    config = vutils.load_config('configs/config.toml')

    # get the logging level:
    if config['logging_level'] == 'debug':
        level = logging.DEBUG
    else:
        level = logging.INFO

    # get log location
    if config['logging_location'] == 'stdout':
        logging.basicConfig(stream=sys.stdout, level=level)
    else:
        night = vutils.get_tonight()
        log_filename = f"{night}_donuts.log"
        log_file_path = f"{config['logging_root']}/{log_filename}"
        logging.basicConfig(filename=log_file_path,
                            level=level,
                            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    # set up Voyager/Donuts
    voyager = Voyager(config)
    # run the script
    voyager.run()
