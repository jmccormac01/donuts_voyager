"""
Test script for guiding Voyager with donuts
"""
import sys
import socket as s
import traceback
import time
import threading
import queue
import json
import uuid
import numpy as np

# TODO: add logging

# pylint: disable=line-too-long

class DonutsStatus():
    """
    Current status of Donuts guiding
    """
    CALIBRATING, GUIDING, IDLE, UNKNOWN = np.arange(4)

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

        # keep track of current status
        self._status = DonutsStatus.UNKNOWN

        self.image_id = 0
        self.last_poll_time = None

        # set up the guiding thread
        self._latest_guide_frame = None
        self._guide_condition = threading.Condition()

        # set up a queue to send back results from guide_loop
        self._results_queue = queue.Queue(maxsize=1)

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
            if rec:
                print(f"RECEIVED: {rec}")

                # handle events
                if 'Event' in rec.keys():

                    if rec['Event'] == "Polling":
                        pass

                    elif rec['Event'] == "DonutsCalibrationRequired":
                        # send a dummy command with a small delay for now
                        self._status = DonutsStatus.CALIBRATING
                        self.__send_donuts_message_to_voyager("DonutsCalibrationStart")
                        time.sleep(5)
                        self.__send_donuts_message_to_voyager("DonutsCalibrationDone")
                        self._status = DonutsStatus.IDLE

                    elif rec['Event'] == "DonutsRecenterRequired":
                        # if guider is IDLE, do stuff, otherwise do nothing
                        if self._status == DonutsStatus.IDLE:
                            # set the current mode to guiding
                            self._status = DonutsStatus.GUIDING
                            # send a DonutsRecenterStart reply
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")

                            # keep a local copy of the image to guide on's path
                            last_image = rec['FitPathAndName']

                            # set the latest image and notify the guide loop thread to wake up
                            with self._guide_condition:
                                self._latest_guide_frame = rec['FitPathAndName']
                                self._guide_condition.notify()

                            # fetch the results from the queue
                            direction, duration = self._results_queue.get()
                            print(f"CORRECTION: {direction['x']}:{duration['x']} {direction['y']}:{duration['y']}")

                            # send a pulseGuide command followed by a done
                            # or by an error command if something happened
                            try:
                                uuid_x = str(uuid.uuid4())
                                self.__send_voyager_pulse_guide(uuid_x, self.image_id, direction['x'], duration['x'])
                                uuid_y = str(uuid.uuid4())
                                self.__send_voyager_pulse_guide(uuid_y, self.image_id, direction['y'], duration['y'])
                                self.image_id += 1

                                # send a DonutsRecenterDone message
                                self.__send_donuts_message_to_voyager("DonutsRecenterDone")
                            except:
                                # send a recentering error
                                self.__send_donuts_message_to_voyager("DonutsRecenterError", f"Failed to PulseGuide {last_image}")

                            # set the current mode back to IDLE
                            self._status = DonutsStatus.IDLE

                        else:
                            print("WARNING: Donuts is busy, skipping...")
                            # send Voyager a start and a done command to keep it happy
                            self.__send_donuts_message_to_voyager("DonutsRecenterStart")
                            self.__send_donuts_message_to_voyager("DonutsRecenterDone")

                    elif rec['Event'] == "DonutsAbort":
                        print("Donuts abort requested, dying peacefully")
                        # close the socket
                        self.__close_socket()
                        # exit
                        sys.exit(0)

                    # handle responses to remote actions
                    elif rec['Event'] == "RemoteActionResult":
                        print("Handle remote action results for a given UID")

                    # erm, something has gone wrong
                    else:
                        print('Oh dear, something unforseen has occurred...')

                # handle basic jsonrpc responses
                elif 'jsonrpc' in rec.keys():
                    if rec['result'] != 0:
                        print(f"ERROR: {rec}")
                    else:
                        print(f"OK: {rec}")

            # do we need to poll again?
            now = time.time()
            time_since_last_poll = now - self.last_poll_time
            if time_since_last_poll > 5:
                # ping the keep alive
                self.__keep_socket_alive()

    def __guide_loop(self):
        """
        Analyse incoming images for guiding offsets
        """
        while 1:
            # block until a frame is available for processing
            with self._guide_condition:
                while self._latest_guide_frame is None:
                    self._guide_condition.wait()

                frame_path = self._latest_guide_frame
                self._latest_guide_frame = None
                # TODO work out guide correction here
                # Update PID loop

                # test case
                print(frame_path)
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
            print('Voyager socket connect failed!')
            print('Check the application interface is running!')
            traceback.print_exc()
            sys.exit(1)

    def __close_socket(self):
        """
        Close the socket once finished
        """
        self.socket.close()

    def __send(self, message):
        """
        Send a message to Voyager
        """
        try:
            # send the command
            self.socket.sendall(bytes(message, encoding='utf-8'))
            sent = True
            # update the last poll time
            self.last_poll_time = time.time()
        except:
            print(f"Error sending message {message} to Voyager")
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
            #print("Socket receive timeout, continuing...")
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
        sent = self.__send(polling_str)
        if sent:
            print(f"SENT: {polling_str.rstrip()}")
        self.last_poll_time = time.time()

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
        sent = self.__send(msg_str)
        if sent:
            print(f"SENT: {msg_str.rstrip()}")
        self.last_poll_time = time.time()

    def __send_voyager_pulse_guide(self, uid, idd, direction, duration):
        """
        Issue the final post-PID loop guide corrections in direction/duration
        format. These values are mapped from X and Y offsets during calibration
        """
        # generate a unique ID for this transmission
        message = {'method': 'RemotePulseGuide',
                   'params': {'UID': uid,
                              'Direction': direction,
                              'Duration': duration},
                   'id': idd}
        msg_str = json.dumps(message) + "\r\n"

        # send the command
        sent = self.__send(msg_str)
        if sent:
            print(f"SENT: {msg_str.rstrip()}")
        self.last_poll_time = time.time()

    #def __image_str(self, exptime):
    #    """
    #    Create a string for taking an image
    #    """
    #    image_dict = {"method": "RemoteCameraShot",
    #                  "params": {"UID": "eaea5429-f5a9-4012-bc9b-f109e605f5d8",
    #                             "Expo": f"{exptime}",
    #                             "Bin": 1,
    #                             "IsROI": "false",
    #                             "ROITYPE": 0,
    #                             "ROIX": 0,
    #                             "ROIY": 0,
    #                             "ROIDX": 0,
    #                             "ROIDY": 0,
    #                             "FilterIndex": 0,
    #                             "ExpoType": 0,
    #                             "SpeedIndex": 0,
    #                             "ReadoutIndex": 0,
    #                             "IsSaveFile": "false",
    #                             "FitFileName": "",
    #                             "Gain": 1,
    #                             "Offset": 0},
    #                  "id": self.image_id}
    #    return json.dumps(image_dict)

if __name__ == "__main__":

    config = {'socket_ip': '127.0.0.1',
              'socket_port': 5950,
              'host': 'DESKTOP-CNTF3JR'}

    voyager = Voyager(config)
    voyager.run()
