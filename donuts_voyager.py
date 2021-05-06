"""
Test script for guiding Voyager with donuts
"""
import sys
import socket as s
import traceback
import time
import threading

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
        #main_thread = threading.Thread(target=self.establish_and_maintain_voyager_connection)
        #main_thread.daemon = True
        #main_thread.start()

        # set up the guiding thread
        #self._guide_condition = threading.Condition()
        #self._guide_latest_frame = None

        # guide_thread = threading.Thread(target=self.__analyse_latest_image)

    def establish_and_maintain_voyager_connection(self):
        """
        Open a connection and maintain it with Voyager
        """
        self.__open_socket()

        while 1:
            # keep it alive and listen for jobs
            polling_str = self.__polling_str()
            sent = self.__send(polling_str)
            if sent:
                print(f"SENT: {polling_str}")

            # listen for a response
            rec = self.__receive()
            if rec:
                print(f"RECEIVED: {rec}")

            time.sleep(1)

    def __open_socket(self):
        """
        Open a connection to Voyager
        """
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.socket.settimeout(2.0)
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
            self.socket.sendall(bytes(message, encoding='utf-8'))
            sent = True
            self.inst += 1
        except:
            print(f"Error sending message {message} to Voyager")
            traceback.print_exc()
            sent = False
        return sent

    def __receive(self, n_bytes=1024):
        """
        Receive a message of n_bytes in length from Voyager
        """
        return self.socket.recv(n_bytes)


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

if __name__ == "__main__":

    config = {'socket_ip': '127.0.0.1',
              'socket_port': 5950,
              'host': 'DESKTOP-CNTF3JR'}

    voyager = Voyager(config)
