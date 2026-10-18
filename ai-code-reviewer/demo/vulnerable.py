import os
import pickle
import hashlib
import subprocess
import yaml


def get_user(cursor, name):
    cursor.execute("SELECT * FROM users WHERE name = '" + name + "'")
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)
    cursor.execute("SELECT * FROM users WHERE name = '{}'".format(name))


def calc(expr):
    return eval(expr)


def run(cmd):
    subprocess.run(cmd, shell=True)


def load(blob):
    return pickle.loads(blob)


def digest(password):
    return hashlib.md5(password.encode()).hexdigest()


def cfg(text):
    return yaml.load(text)


def read(path):
    f = open(path)
    try:
        return f.read()
    except:
        pass
