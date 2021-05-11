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

# TODO: add logging

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

        # set up the main polling thread
        main_thread = threading.Thread(target=self.establish_dispatcher)
        main_thread.daemon = True
        main_thread.start()

        self.image_id = 0
        self.last_poll_time = None

        # set up the guiding thread
        #self._guide_condition = threading.Condition()
        #self._guide_latest_frame = None
        # guide_thread = threading.Thread(target=self.__analyse_latest_image)

        # set up the calibration

    def establish_dispatcher(self):
        """
        Open a connection and maintain it with Voyager
        """
        # open the socket to Voyager
        self.__open_socket()

        # keep it alive and listen for jobs
        self.__keep_socket_alive()

        # fifo for commands to send to Voyager
        commands = queue.Queue(maxsize=0)

        # loop until told to stop
        while 1:
            # listen for a response or a new job to do
            rec = self.__receive()
            if rec:
                print(f"RECEIVED: {rec}")

                if rec['Event'] == "Polling":
                    pass
                elif rec['Event'] == "DonutsCalibrationRequired":
                    print("Do donuts calibration")
                    pass
                elif rec['Event'] == "DonutsRecenterRequired":
                    print("Do donuts recentering")
                    pass
                elif rec['Event'] == "DonutsAbort":
                    print("Donuts abort requested, dying peacefully")
                    sys.exit(0)
                else:
                    print('Oh dear, something unforseen has occurred...')
                    pass

                # TODO: dispatch jobs here!
                # NOTE: donuts calibration:
                #       1. SEND calibration start
                #       2. DO calibration procedure: cross pattern with images
                #       3. Analyse the dat, update the config for direction/magnitude
                #       4. SEND calibration end (or calibration error if failure)
                # NOTE: donuts abort
                #       1. If recieved, stop all threads and end this code
                # NOTE: donuts recenter <path>
                #       1. SEND recenter star
                #       2. Do recentering calculation (including PID loop)
                #       3. Prepare a response for Voyager
                #       4. SEND recenter done (or recenter error if failure)
                # TODO: add communications with Voyager to commands queue

            # do we need to poll again?
            now = time.time()
            time_since_last_poll = now - self.last_poll_time
            if time_since_last_poll > 5 and commands.empty():
                # ping the keep alive
                self.__keep_socket_alive()

            # here we pass on any communication to Voyager
            while not commands.empty():
                next_command = commands.get()
                sent = self.__send(next_command)
                if sent:
                    print(f"SENT: {next_command}")


            #time.sleep(1)

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
            print("Socket receive timeout, continuing...")
        return message

    def __keep_socket_alive(self):
        """
        Convenience method to keep socket open
        """
        polling_str = self.__polling_str()
        sent = self.__send(polling_str)
        if sent:
            print(f"SENT: {polling_str}")
        self.last_poll_time = time.time()

    def __polling_str(self):
        """
        Create a polling string
        """
        now = str(time.time())
        return f"{{\"Event\":\"Polling\",\"Timestamp\":{now},\"Host\":\"{self.host}\",\"Inst\":{self.inst}}}\r\n"

    def __guide_str(self):
        """
        Create a guiding string
        """
        return ""

    def __image_str(self, exptime):
        """
        Create a string for taking an image
        """
        image_dict = {"method": "RemoteCameraShot",
                      "params": {"UID": "eaea5429-f5a9-4012-bc9b-f109e605f5d8",
                                 "Expo": f"{exptime}",
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
                                 "IsSaveFile": "false",
                                 "FitFileName": "",
                                 "Gain": 1,
                                 "Offset": 0},
                      "id": self.image_id}
        return json.dumps(image_dict)

if __name__ == "__main__":

    config = {'socket_ip': '127.0.0.1',
              'socket_port': 5950,
              'host': 'DESKTOP-CNTF3JR'}

    voyager = Voyager(config)
