#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Columbia EECS E6893 Big Data Analytics

from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row, SQLContext
from pyspark import StorageLevel
import sys, getopt
import requests
import time, pytz, datetime
import subprocess
import re
from google.cloud import bigquery

# Helper functions
def saveToStorage(rdd, output_directory, columns_name, mode):
    """
    Save each RDD in this DStream to google storage
    Args:
        rdd: input rdd
        output_directory: output directory in google storage
        columns_name: columns name of dataframe
        mode: mode = "overwirte", overwirte the file
              mode = "append", append data to the end of file
    """
    if not rdd.isEmpty():
        (rdd.toDF(columns_name)
         .write.save(output_directory, format="json", mode=mode))


def saveToBigQuery(sc, output_dataset, output_table, directory):
    """
    Put temp streaming json files in google storage to google BigQuery
    and clean the output files in google storage
    """
    files = directory + '/part-*.json'
    subprocess.check_call(
        'bq load --source_format NEWLINE_DELIMITED_JSON '
        '--replace '
        '--autodetect '
        '{dataset}.{table} {files}'.format(
            dataset=output_dataset, table=output_table, files=files
        ).split())
    output_path = sc._jvm.org.apache.hadoop.fs.Path(directory)
    output_path.getFileSystem(sc._jsc.hadoopConfiguration()).delete(
        output_path, True)


def sendPartition(iter):
    for record in iter:
        print(record)


def aggregateTagsCount(new_values, total_sum):
    return sum(new_values) + (total_sum or 0)

def hashtagExtract(words, window_duration, slide_duration):
    def combineSimilarTags(word):
        tagsPool = ["#covid19", "#covid", "#coronavirus", "#covid-19", "#covid_19", "#covidー19", "#covid2019",
                    "covid19-virus", "#covid__19"]
        if word.lower() in tagsPool:
            return "#covid19"
        else:
            return word

    def removeLastPunctuation(word):
        punctuationPool = [",", ".", "!", "?",":","-",")"]
        if word[len(word)-1] in punctuationPool:
            return word[0:len(word)-1]
        else:
            return word

    def is_valid(word):
        flag = True
        invalid_word_pool = ["#breaking", "#watch"]
        if "…" in word: flag = False
        if "@" in word: flag = False
        if word[len(word)-2:len(word)].lower() == "rt": flag = False
        if len(word) <= 1: flag = False
        if word.lower() in  invalid_word_pool: flag = False
        return flag

    # words = words.map(lambda word: word.lower())
    pattern = re.compile("#")
    hashtags = words.filter(lambda word: pattern.match(word, 0)) \
                    .filter(lambda word: is_valid(word)) \
                    .map(lambda word: removeLastPunctuation(word)) \
                    .map(lambda word: combineSimilarTags(word))

    hashtagsTotalSorted = hashtags.map(lambda word: (word, 1)) \
                                  .reduceByKeyAndWindow(lambda x, y: x+y, lambda x, y: x-y,
                                                        windowDuration=window_duration,
                                                        slideDuration=slide_duration) \
                                  .transform(lambda rdd: rdd.sortBy(lambda word: word[1], False))

    # hashtagsTotalSorted.foreachRDD(lambda rdd: rdd.foreachPartition(sendPartition))
    return hashtagsTotalSorted



def toCSVLine(data):
    return ','.join(str(d) for d in data)

def main(argv):
    # parameter
    IP = 'localhost'  # ip port
    PORT = 9001
    location_abbr = "NY"

    try:
        opts, args = getopt.getopt(argv, "p:a:")

    except getopt.GetoptError:
        print('error')
        sys.exit(2)
    for opt, arg in opts:
        if opt in "-p":
            PORT = int(arg)
            print("PORT =", PORT)
        elif opt in "-a":
            location_abbr = arg
            print(location_abbr)

    # global variables
    # bucket = "bucket-hashtags-"+location_abbr.lower()  # TODO : replace with your own bucket name
    bucket = "test-bucket-hashtags"
    output_directory_hashtags = 'gs://{}/hadoop/tmp/bigquery/pyspark_output/hashtagsCount/{}'.format(bucket, location_abbr.lower())

    # output table and columns name
    output_dataset = 'hashtag_dataset'  # the name of your dataset in BigQuery
    output_table_hashtags = 'hashtags'+location_abbr
    columns_name_hashtags = ['hashtags', 'count']

    STREAMTIME = 120  # time that the streaming process runs

    # Spark settings
    conf = SparkConf()
    conf.setMaster("local[2]")
    conf.setAppName("TwitterStreamApp")

    # create spark context with the above configuration
    sc = SparkContext(conf=conf)
    sc.setLogLevel("ERROR")

    # create sql context, used for saving rdd
    sql_context = SQLContext(sc)

    # create the Streaming Context from the above spark context with batch interval size 5 seconds
    ssc = StreamingContext(sc, 5)
    # setting a checkpoint to allow RDD recovery
    ssc.checkpoint("checkpointSpark")

    # read data from port
    dataStream = ssc.socketTextStream(IP, PORT, StorageLevel.MEMORY_AND_DISK)
    # dataStream = ssc.textFileStream("./textfiles/")
    # dataStream.pprint()

    words = dataStream.flatMap(lambda line: line.split(" "))
    # words.pprint()

    # extract the hashtags in the tweets
    hashtagsTotalsSorted = hashtagExtract(words, window_duration=10, slide_duration=10)
    hashtagsTotalsSorted.pprint()

    hashtagsTotalsSorted.foreachRDD(
        lambda rdd: saveToStorage(rdd, output_directory_hashtags, columns_name_hashtags, mode="overwrite")
    )

    # start streaming process, wait and then stop.
    ssc.start()
    time.sleep(185)
    # ssc.awaitTermination()
    ssc.stop(stopSparkContext=False, stopGraceFully=True)

    saveToBigQuery(sc, output_dataset, output_table_hashtags, output_directory_hashtags)

if __name__ == "__main__":
    main(sys.argv[1:])
