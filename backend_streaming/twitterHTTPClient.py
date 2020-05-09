#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is used to pull data from twitter API and send data to
Spark Streaming process using socket. It acts like a client of
twitter API and a server of spark streaming. It open a listening TCP
server socket, and listen to any connection from TCP client. After
a connection established, it send streaming data to it.


Usage:
  If used with dataproc:
    gcloud dataproc jobs submit pyspark --cluster <Cluster Name> twitterHTTPClient.py

  Make sure that you run this module before you run spark streaming process.
  Please remember stop the job on dataproc if you no longer want to stream data.

Todo:
  1. change the credentials to your own

"""

import tweepy
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
import socket
import json
import sys, getopt

# credentials
# TODO: replace with your own credentials
ACCESS_TOKEN = '1185444894938193920-9dTDW9Z9G0LUnW2Xlkt6qTyMB3qeCR'     # your access token
ACCESS_SECRET = 'AZdOiKPg5xiJ4Cz2qMfg5J1uIBUnlgVjR3uG0AiNCM22x'    # your access token secret
CONSUMER_KEY = 'fWVcVFfkPt5fGcfyB1Tcd2foC'     # your API key
CONSUMER_SECRET = 'xZkP6Wmu0LOwocBZzA54dy76uackTYIpZgYULoNWP0hxG2xf11'  # your API secret key



class TweetsListener(StreamListener):
    """
    tweets listener object
    """
    def __init__(self, csocket):
        self.client_socket = csocket
    def on_data(self, data):
        try:
            msg = json.loads( data )
            print('TEXT:{}\n'.format(msg['text']))
            self.client_socket.send( msg['text'].encode('utf-8') )
            return True
        except BaseException as e:
            print("Error on_data: %s" % str(e))
            return False
        # return True
    def on_error(self, status):
        print(status)
        return False


class twitter_client:
    def __init__(self, TCP_IP, TCP_PORT, LOCATION, TAGS):
      self.s = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s.bind((TCP_IP, TCP_PORT))
      self.location = LOCATION
      self.tags = tags

    def run_client(self):
      try:
        self.s.listen(1)
        while True:
          print("Waiting for TCP connection...")
          conn, addr = self.s.accept()
          print("Connected... Starting getting tweets.")
          self.sendData(conn)
          conn.close()
          break
      except KeyboardInterrupt:
        exit

    def sendData(self, c_socket):
        tags = self.tags
        location = self.location
        loc = location.split(",")
        loc = [float(i) for i in loc]
        location = [loc[1], loc[0], loc[3], loc[2]]
        auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
        twitter_stream = Stream(auth, TweetsListener(c_socket))  # bind the input Tweeter stream to my personal stream
        twitter_stream.filter(track=tags,
                              languages=['en'],
                              # filter_level='medium'
                              locations=location
                              )

if __name__ == '__main__':
    argv = sys.argv[1:]
    port = 9001
    location_ini = "NY"

    # the tags to track
    # tags = ['#COVID19', '#CORONAVIRUS', '#covid']
    tags = ["#covid19", "#covid", "#coronavirus", "#covid-19", "#covid_19", "#covidー19", "#covid2019",
     "covid19-virus", "#covid__19"]
    try:
        opts, args = getopt.getopt(argv, "l:p:")
    except getopt.GetoptError:
        print('error')
        sys.exit(2)
    for opt, arg in opts:
        if opt in "-l":
            location_ini = arg
        elif opt in "-p":
            port = int(arg)

    client = twitter_client("localhost", port, location_ini, tags)
    client.run_client()

