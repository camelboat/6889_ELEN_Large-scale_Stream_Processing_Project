import os
import csv

class SingleDeployer:
    # loc_val should be a string object, such as "0,1,2,3"
    def __init__(self, port, loc_val, loc_abbr, cluster_name, twitter_file_name, spark_file_name):
        self.port = port
        self.loc_val = loc_val[0]+","+loc_val[1]+","+loc_val[2]+","+loc_val[3]
        self.loc_abbr = loc_abbr
        self.cluster_name = cluster_name
        self.twitter_file_name = twitter_file_name
        self.spark_file_name = spark_file_name
        self.command = "gcloud dataproc jobs submit pyspark --cluster {} ".format(self.cluster_name)
        self.flags_twitter = " --async --region=us-east1"
        self.flags_spark = " --region=us-east1"

    def deploy_twitter_stream(self):
        command = self.command + self.twitter_file_name
        args = " -- -l {} -p {}".format(self.loc_val, str(self.port))
        command = command + self.flags_twitter + args
        print(command)
        os.system(command)

    def deploy_spark_stream(self):
        command = self.command + self.spark_file_name
        args = " -- -p {} -a {}".format(str(self.port), self.loc_abbr)
        command = command + self.flags_spark + args
        print(command)
        os.system(command)

    def create_bucket(self):
        command = "gsutil mb gs://{}/".format("bucket-hashtags-"+self.loc_abbr.lower())
        print(command)
        os.system(command)


location_data = []
with open('US_locations.csv') as location_file:
    reader = csv.reader(location_file, delimiter=',')
    for line in reader:
        location_data.append(line)

print(location_data)
print(len(location_data))

start_port = 8888
cluster_name = "cluster-twitter"
twitter_file_name = "twitterHTTPClient.py"
spark_file_name = "sparkStreaming.py"

# for num in range(len(location_data)):

# NY - 32
# CA - 4
# MI - 22
# TX - 43
# while True:
for num in [52]:
# for num in range(52):
    port = start_port + num
    location = location_data[num]
    loc_val = location[2:6]
    loc_abbr = location[1]
    tmp_deployer = SingleDeployer(port=port,
                                  loc_val = loc_val,
                                  loc_abbr = loc_abbr,
                                  cluster_name = cluster_name,
                                  twitter_file_name = twitter_file_name,
                                  spark_file_name = spark_file_name
                                  )
    # tmp_deployer.create_bucket()
    tmp_deployer.deploy_twitter_stream()
    tmp_deployer.deploy_spark_stream()
