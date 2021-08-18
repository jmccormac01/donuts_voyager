"""
Test script for communication with Voyager

Note, this is outside Docker and is setup for my
Windows PC
"""
import sys
import socket as s
import traceback
import time
import json


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
        self.message_overflow = []

        # test the new receive_until method
        self.establish_and_maintain_voyager_connection()

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
            rec = self.__receive_until(delim=b'\r\n')
            if rec:
                print(f"RECEIVED: {rec}")

            time.sleep(1)

    def __open_socket(self):
        """
        Open a connection to Voyager
        """
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        #self.socket.settimeout(2.0)
        self.socket.settimeout(0)
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

    def __receive(self, n_bytes=2048):
        """
        Receive a message of n_bytes in length from Voyager

        Parameters
        ----------
        n_bytes : int, optional
            Number of bytes to read from socket
            default = 2048

        Returns
        -------
        message : dict
            json parsed response from Voyager

        Raises
        ------
        None
        """
        # NOTE original code, we have JSON decoding errors, trying to figure it out
        #try:
        #    message = json.loads(self.socket.recv(n_bytes))
        #except s.timeout:
        #    message = {}
        #return message

        # load the raw string
        try:
            message_raw = self.socket.recv(n_bytes)
        except s.timeout:
            message_raw = ""

        # unpack it into a json object
        if message_raw != "":
            # NOTE sometimes a message is truncated, try to stop it crashing...
            try:
                message = json.loads(message_raw)
            except json.decoder.JSONDecodeError:
                message = {}
        else:
            message = {}

        return message

    def __receive_until(self, delim=b'\r\n'):
        """
        """
        message_buffer = []
        n_bytes = 2048

        # check if there is any overflow from last time
        print(f"Message overflow {self.message_overflow}")
        for msg in self.message_overflow:
            print("HANDLING OVERFLOW!!!!!!!!!")
            message_buffer.append(msg)

        # reset the overflow
        self.message_overflow = []
        print(f"Message overflow {self.message_overflow}")

        continue_reading = True
        while continue_reading:
            message_raw = self.socket.recv(n_bytes)
            print(f"Message raw {message_raw}")

            if delim in message_raw:
                print("DELIM FOUND...")
                continue_reading = False
                message_end, message_new_start = message_raw.split(b'\r\n')
                print(f"Message parts {message_end} : {message_new_start}")
                message_buffer.append(message_end)
                print(f"Message buffer: {message_buffer}")
                self.message_overflow.append(message_new_start)
                print(f"Message overflow: {self.message_overflow}")

            else:
                print("DELIM NOT FOUND, CONTINUING READING...")
                continue_reading = True
                message_buffer.append(message_raw)

        print("DONE READING...")
        message_str = b''.join(message_buffer)
        print(f"Final message string: {message_str}")
        return json.loads(message_str)

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
