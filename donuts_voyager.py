"""
Test script for guiding Voyager with donuts
"""
import os
import sys
import socket as s
import traceback
import time
import threading
import queue
import json
import uuid
import numpy as np
import voyager_utils as vutils

# TODO: Add logging
# TODO: Add RemoteActionAbort call when things go horribly wrong
# TODO: Determine how to trigger/abort donuts script from drag_script
# this has been ignored for now while testing

# pylint: disable=line-too-long
# pylint: disable=invalid-name

class DonutsStatus():
    """
    Current status of Donuts guiding
    """
    CALIBRATING, GUIDING, IDLE, UNKNOWN = np.arange(4)

class Message():
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
        """
        # TODO: add more features? (filter etc?)
        # do we need that?
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

        Also return the response code that says things
        went well. Typically 4

        RA and DEC should be in HH MM SS.ss ±DD MM SS.ss format
        In this format we set IsText = true and set 0's for RA and DEC.
        We give the coords in the RAText and DECText arguments
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

class Response():
    """
    Keep track of outstanding responses from Voyager
    """
    def __init__(self, uid, idd, ok_status):
        """
        Initialise response object
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
        """
        self.uid_recv = True
        self.uid_status = status

    def idd_received(self, status):
        """
        Update uuid response as received
        """
        self.idd_recv = True
        self.idd_status = status

    def all_ok(self):
        """
        Check if uid and idd are all ok
        Return True if so and False if not

        idd is left hardcoded to 0
        uid code is supplied
        """
        return self.uid_recv and self.idd_recv and \
               self.uid_status == self.ok_status and self.idd_status == 0

class Voyager():
    """
    Voyager interaction class
    """
    def __init__(self, config):
        """
        Initialise the class
        """
        self.socket = None
        self.socket_ip = config['socket_ip']
        self.socket_port = config['socket_port']
        self.host = config['host']
        self.inst = 1
        self.image_extension = config['image_extension']

        # Fits image path keyword
        self._voyager_path_keyword = "FITPathAndName"
        self._INFO_SIGNALS = ["Polling", "Version", "Signal", "NewFITReady"]

        # keep track of current status
        self._status = DonutsStatus.UNKNOWN

        # add a message object for sharing between methods
        self._msg = Message()

        self._image_id = 0
        self._comms_id = 0
        self._last_poll_time = None

        # set up the guiding thread
        self._latest_guide_frame = None
        self._guide_condition = threading.Condition()

        # set up a queue to send back results from guide_loop
        self._results_queue = queue.Queue(maxsize=1)

        # set up some callback parameters
        self._CB_LOOP_LIMIT = 10

        # set up some calibration dir info
        self.calibration_root = config['calibration_root']
        if not os.path.exists(self.calibration_root):
            os.mkdir(self.calibration_root)
        # this calibration directory inside calibration root gets made if we calibrate
        self.calibration_dir = None
        self.calibration_step_size_ms = config['calibration_step_size_ms']
        self.calibration_n_iterations = config['calibration_n_iterations']
        self.calibration_exptime = config['calibration_exptime']

    def __calibration_filename(self, direction, pulse_time):
        """
        Return a calibration filename
        """
        return f"{self.calibration_dir}\\step_{self._image_id}_d{direction}_{pulse_time}ms{self.image_extension}"

    def __calibrate_donuts(self):
        """
        Run the calibration routine

        Take in the message object so we can prepare commands
        """
        # set up calibration directory
        self.calibration_dir, _ = vutils.get_data_dir(self.calibration_root)

        # point the telescope to 1h west of the meridian

        # make it the reference for Donuts

        # calculate the shift and store result

        # determine direction and ms/pix scaling



        # get the reference filename
        filename = self.__calibration_filename("R", 0)
        shot_uuid = str(uuid.uuid4())
        # take an image at the current location
        try:
            message_shot = self._msg.camera_shot(shot_uuid, self._comms_id, self.calibration_exptime, "true", filename)
            self.__send_two_way_message_to_voyager(message_shot)
            self._comms_id += 1
            self._image_id += 1
        except Exception:
            self.__send_donuts_message_to_voyager("DonutsCalibrationError", f"Failed to take image {filename}")

        # TODO: Make this the reference image or do calibration externally

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
                    self._image_id += 1
                except Exception:
                    # send a recentering error
                    self.__send_donuts_message_to_voyager("DonutsRecenterError", f"Failed to PulseGuide {i} {self.calibration_step_size_ms}")
                    traceback.print_exc()

                # take an image
                try:
                    filename = self.__calibration_filename(i, self.calibration_step_size_ms)
                    shot_uuid = str(uuid.uuid4())
                    message_shot = self._msg.camera_shot(shot_uuid, self._comms_id, self.calibration_exptime, "true", filename)
                    self.__send_two_way_message_to_voyager(message_shot)
                    self._comms_id += 1
                    self._image_id += 1
                except Exception:
                    self.__send_donuts_message_to_voyager("DonutsCalibrationError", f"Failed to take image {filename}")

    def run(self):
        """
        Open a connection and maintain it with Voyager
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
            # listen for a response or a new job to do
            rec = self.__receive()

            # was there a command? If so, do something, else, do nothing/keep alive
            if rec:

                # handle events
                if 'Event' in rec.keys():

                    # do nothing for events that just give us some info
                    if rec['Event'] in self._INFO_SIGNALS:
                        print(f"RECEIVED: {rec}")

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
                        print(f"RECEIVED: {rec}")
                        # if guider is IDLE, do stuff, otherwise do nothing
                        if self._status == DonutsStatus.IDLE:
                            # set the current mode to guiding
                            self._status = DonutsStatus.GUIDING
                            # send a DonutsRecenterStart reply
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")

                            # keep a local copy of the image to guide on's path
                            last_image = rec[self._voyager_path_keyword]

                            # set the latest image and notify the guide loop thread to wake up
                            with self._guide_condition:
                                self._latest_guide_frame = rec[self._voyager_path_keyword]
                                self._guide_condition.notify()

                            # fetch the results from the queue
                            direction, duration = self._results_queue.get()
                            print(f"CORRECTION: {direction['x']}:{duration['x']} {direction['y']}:{duration['y']}")

                            # send a pulseGuide command followed by a loop for responses
                            # this must be done before the next command can be sent
                            # if both are sent ok, we send the DonutsRecenterDone, otherwise we send an error
                            try:
                                # make x correction message
                                uuid_x = str(uuid.uuid4())
                                message_x = self._msg.pulse_guide(uuid_x, self._comms_id, direction['x'], duration['x'])
                                # send x correction
                                self.__send_two_way_message_to_voyager(message_x)
                                self._comms_id += 1

                                # make y correction message
                                uuid_y = str(uuid.uuid4())
                                message_y = self._msg.pulse_guide(uuid_y, self._comms_id, direction['y'], duration['y'])
                                # send the y correction
                                self.__send_two_way_message_to_voyager(message_y)
                                self._comms_id += 1

                                # send a DonutsRecenterDone message
                                self.__send_donuts_message_to_voyager("DonutsRecenterDone")
                            except Exception:
                                # send a recentering error
                                self.__send_donuts_message_to_voyager("DonutsRecenterError", f"Failed to PulseGuide {last_image}")
                                traceback.print_exc()

                            # set the current mode back to IDLE
                            self._status = DonutsStatus.IDLE

                        # ignore commands if we're already doing something
                        else:
                            print("WARNING: Donuts is busy, skipping...")
                            # send Voyager a start and a done command to keep it happy
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")
                            self.__send_donuts_message_to_voyager("DonutsRecenterDone")

                    # handle the abort event
                    elif rec['Event'] == "DonutsAbort":
                        print(f"RECEIVED: {rec}")
                        print("EVENT: Donuts abort requested, dying peacefully")
                        # close the socket
                        self.__close_socket()
                        # exit
                        sys.exit(0)

                    # erm, something has gone wrong
                    else:
                        print('ERROR: Oh dear, something unforseen has occurred. Here\'s what...')
                        print(f"ERROR: Failed parsing {rec}")

            # do we need to poll again?
            now = time.time()
            time_since_last_poll = now - self._last_poll_time
            if time_since_last_poll > 5:
                # ping the keep alive
                self.__keep_socket_alive()

    def __guide_loop(self):
        """
        Analyse incoming images for guiding offsets
        """
        while 1:
            # TODO: add something to permit ending this thread cleanly

            # block until a frame is available for processing
            with self._guide_condition:
                while self._latest_guide_frame is None:
                    self._guide_condition.wait()

                frame_path = self._latest_guide_frame
                self._latest_guide_frame = None
                # TODO work out guide correction here
                # Update PID loop

                # test case
                print(f"INFO: filename = {frame_path}")
                direction = {"x": 0, "y": 2}
                duration = {"x": 1000, "y": 500}
                self._results_queue.put((direction, duration))

    def __open_socket(self):
        """
        Open a connection to Voyager
        """
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.socket.settimeout(1.0)
        try:
            self.socket.connect((self.socket_ip, self.socket_port))
        except s.error:
            print('ERROR: Voyager socket connect failed!')
            print('ERROR: Check the application interface is running!')
            traceback.print_exc()
            sys.exit(1)

    def __close_socket(self):
        """
        Close the socket once finished
        """
        self.socket.close()

    def __send(self, message, n_attempts=3):
        """
        Send a message to Voyager
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
                print(f"SENT: {message.rstrip()}")
            except:
                print(f"ERROR: CANNOT SEND {message} TO VOYAGER [{n_attempts}]")
                traceback.print_exc()
                sent = False

        return sent

    def __receive(self, n_bytes=1024):
        """
        Receive a message of n_bytes in length from Voyager
        """
        try:
            message = json.loads(self.socket.recv(n_bytes))
        except s.timeout:
            message = {}
        return message

    def __keep_socket_alive(self):
        """
        Convenience method to keep socket open
        """
        now = str(time.time())
        polling = {"Event": "Polling",
                   "Timestamp": now,
                   "Host": self.host,
                   "Inst": self.inst}

        # send the polling string
        polling_str = json.dumps(polling) + "\r\n"
        _ = self.__send(polling_str)
        # TODO: do something if not sent?

    @staticmethod
    def __parse_jsonrpc(response):
        """
        Take a jsonrpc response and figure out
        what happened. If there is an error result is
        missing and error object is there instead
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
        """
        result = response['ActionResultInt']
        uid = response['UID']
        motivo = response['Motivo']
        param_ret = response['ParamRet']
        return uid, result, motivo, param_ret

    def __send_donuts_message_to_voyager(self, event, error=None):
        """
        Acknowledge a command from Voyager
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
        # TODO: do something if not sent?

    def __send_abort_message_to_voyager(self, uid, idd):
        """
        If things go pear shaped and donuts is quitting,
        tell Voyager to abort this UID:IDD also
        """
        message = {'method': 'RemoteActionAbort',
                   'params': {'UID': uid},
                   'id': idd}
        msg_str = json.dumps(message) + "\r\n"

        # send the command
        _ = self.__send(msg_str)
        # TODO: do something if not sent?

        # TODO: we should probably wait to check the jsonrpc for abort here also
        # skip this for now. I think we need a generic send/receive method. Will
        # bake it into that later

    def __send_two_way_message_to_voyager(self, message):
        """
        Issue any two way command to Voyager

        Wait for the initial jsonrpc response, act accordingly
        If all good, wait for the RemoteActionResult event, act accordingly
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
                        print(f"CALLBACK ADD: {uid}:{idd}")


                print(f"INFO: JSONRPC CALLBACK LOOP [{cb_loop_count+1}]: {uid}:{idd}")
                rec = self.__receive()

                # handle the jsonrpc response (1 of 2 responses needed)
                if "jsonrpc" in rec.keys():
                    print(f"RECEIVED: {rec}")
                    rec_idd, result, err_code, err_msg = self.__parse_jsonrpc(rec)

                    # we only care bout IDs for the commands we just sent right now
                    if rec_idd == idd:
                        # result = 0 means OK, anything else is bad
                        # leave this jsonrpc check hardcoded
                        if result != 0:
                            print(f"ERROR: Problem with command id: {idd}")
                            print(f"ERROR: {err_code} {err_msg}")
                            # Leo said if result!=0, we have a serious issue. Therefore abort.
                            self.__send_abort_message_to_voyager(uid, idd)
                            raise Exception("ERROR: Could not send pulse guide command")
                        else:
                            print(f"INFO: Command id: {idd} returned correctly")
                            # add the response if things go well. if things go badly we're quitting anyway
                            response.idd_received(result)
                    else:
                        print(f"WARNING: Waiting for idd: {idd}, ignoring response for idd: {rec_idd}")

                # increment loop counter to keep track of how long we're waiting
                cb_loop_count += 1

            # if we exit the while loop above we can assume that
            # we got a jsonrpc response to the pulse guide command
            # here we start listening for it being done
            print(f"INFO: EVENT CALLBACK LOOP [{cb_loop_count+1}]: {uid}:{idd}")
            rec = self.__receive()

            # handle the RemoteActionResult response (2 of 2 needed)
            if "Event" in rec.keys():

                if rec['Event'] == "RemoteActionResult":
                    print(f"RECEIVED: {rec}")
                    rec_uid, result, *_ = self.__parse_remote_action_result(rec)

                    # check we have a response for the thing we want
                    if rec_uid == uid:
                        # result = 4 means OK, anything else is an issue
                        if result != self._msg.OK:
                            print(f"ERROR: Problem with command uid: {uid}")
                            print(f"ERROR: {rec}")
                            # TODO: Consider adding a RemoteActionAbort here if shit hits the fan
                        else:
                            print(f"INFO: Command uid: {uid} returned correctly")
                            # add the response, regardless if it's good or bad, so we can end this loop
                            response.uid_received(result)
                    else:
                        print(f"WARNING: Waiting for uid: {uid}, ignoring response for uid: {rec_uid}")

                elif rec['Event'] in self._INFO_SIGNALS:
                    print(f"RECEIVED: {rec}")

                else:
                    print(f"WARNING [1]: Unknown response {rec}")

            # no response? do nothing
            elif not rec.keys():
                pass
            else:
                print(f"WARNING [2]: Unknown response {rec}")

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
            raise Exception("ERROR: Could not send pulse guide command")

if __name__ == "__main__":

    config = {'socket_ip': '127.0.0.1',
              'socket_port': 5950,
              'host': 'DESKTOP-CNTF3JR',
              'calibration_root': 'C:\\Users\\user\\Documents\\Voyager\\DonutsCalibration',
              'calibration_step_size_ms': 5000,
              'calibration_n_iterations': 3,
              'calibration_exptime': 10,
              'image_extension': ".fit"}

    voyager = Voyager(config)
    voyager.run()
