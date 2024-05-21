import socket
import sys
import os
import glob
import subprocess
import shutil
from _thread import *
import threading
import time
import protocol
import sqlite3
from sqlite3 import Error
import hashlib
import secrets


IP = "0.0.0.0"
PORT = 1234
BIG_BUFFER = 255
user_list = {}
PATH = "database.sqlite"


def create_table():
    conn = sqlite3.connect(PATH)  # creates connection. also creates file if it doesn't exist already
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password_hash TEXT NOT NULL, 
                        salt TEXT NOT NULL
                    )''')  # creates table named users (if it doesn't exist) with ids, usernames, and passwords

    conn.commit()  # commits changes
    conn.close()  # closes connection


def delete_table(table_name):
    conn = sqlite3.connect(PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS {}".format(table_name))

    conn.commit()
    conn.close()


def add_to_table(username, password):
    conn = sqlite3.connect(PATH)
    cursor = conn.cursor()

    salt = secrets.token_hex(16)  # Generate a 16-byte salt
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()  # Hash password + salt

    cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                   (username, hashed_password, salt))

    conn.commit()
    conn.close()


def check_log_in(c, username, password):
    conn = sqlite3.connect(PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result:
        stored_hash, salt = result
        hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()

        if hashed_password == stored_hash:
            c.send(packed("log_in_acc"))
        else:
            c.send(packed("log_in_err"))
    else:
        c.send(packed("log_in_err"))

    conn.close()


def check_register(c, username, password):
    conn = sqlite3.connect(PATH)
    cursor = conn.cursor()

    # checks if there's a user with the same username only
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()  # fetches result

    conn.close()

    if result:
        c.send(packed("error_registering_name"))
    else:
        add_to_table(username, password)
        c.send(packed("registered"))


def packed(cmd):
    return cmd.encode()


def handle_client(c):
    while True:
        cmd = c.recv(BIG_BUFFER).decode()  # gets command sent by client
        print(cmd)
        if protocol.check_cmd(cmd):
            cmd_arr = cmd.split("-")
            command = cmd_arr[0]
            cmd_arr.remove(command)  # removes the command to leave only the params
            params = cmd_arr
            if command == "register":
                if params[1] != params[2]:
                    c.send(packed("error_registering_pass"))
                else:
                    check_register(c, params[0], params[1])
            if command == "log_in":
                check_log_in(c, params[0], params[1])
            if command == "exit":
                break

    c.close()


def main():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((IP, PORT))
        server_socket.listen(5)
    except Exception as err:
        print(err)  # could be an error regarding sockets and the accepting of the client
    # handles requests until user asks to exit
    while True:
        # Checks if protocol is OK, e.g. length field OK
        try:
            client_socket, ipaddress = server_socket.accept()
            x = threading.Thread(target=handle_client, args=(client_socket,))
            x.start()  # communication with client
            create_table()

        except Exception as e:
            print(e)  # could be an error regarding the protocol's functions

    # close sockets
    print("Closing connection")


if __name__ == '__main__':
    main()
