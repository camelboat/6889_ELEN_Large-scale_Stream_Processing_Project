import json, csv
import google.auth
import numpy as np
from google.cloud import bigquery
from google.cloud import bigquery_storage_v1beta1
from google.oauth2 import service_account
from tweepy.parsers import JSONParser
import collections
import tweepy

class JSDumper:
    # cases_data: confirmed cases+deaths
    def __init__(self, file_dir, new_data, cases_data, output_dir):
        self.file_dir = file_dir
        self.new_data = new_data
        self.cases_data = cases_data
        with open(self.file_dir) as dataFile:
            data = dataFile.read()
            obj = data[data.find('{'): data.rfind('}') + 1]
            self.data = json.loads(obj)
        self.output_dir = output_dir

    def dump(self):
        # update today's cases
        df2 = self.cases_data[self.cases_data['date'] == self.cases_data['date'].max()]
        confirmed_cases = list(df2['confirmed_cases'])
        deaths = list(df2['deaths'])

        for i in range(len(self.data["features"])):
            loc_id = self.data["features"][i]['id']
            data_frame = self.new_data[loc_id]
            if not data_frame is None:
                count = data_frame['f0_']
                hashtags = data_frame['hashtags']
                self.data["features"][i]['properties']['topics'] = {}
                for k in np.arange(10) + 1:
                    self.data["features"][i]['properties']['topics'][hashtags[k]] = int(count[k])

            # add confirmed cases & deaths (no puerto rico)
            if i < len(self.data["features"]) - 1:
                self.data['features'][i]['properties']['confirmed_cases'] = int(confirmed_cases[i])
                self.data['features'][i]['properties']['deaths'] = int(deaths[i])

        with open(self.output_dir, 'w') as f:
            json.dump(self.data, f, separators=(',', ':'))
        return self

    def test(self):
        print(len(self.data["features"]))


class BigQueryReader:
    def __init__(self, location_dict, file_dir, output_dir):
        self.location_dict = location_dict
        self.credentials, self.project_id = service_account.Credentials.from_service_account_file(
            'StreamProcessing-8944b82fc244.json'), 'streamprocessing'
        self.bqclient = bigquery.Client(
            credentials=self.credentials,
            project=self.project_id
        )
        self.bqstorageclient = bigquery_storage_v1beta1.BigQueryStorageClient(
            credentials=self.credentials
        )

        self.query_string = """
        SELECT SUM(count), hashtags
        FROM `hashtag_dataset.hashtags{}`
        GROUP BY hashtags
        ORDER BY SUM(count) DESC
        LIMIT 11
        """

        self.query_string2 = """
        select state, date, sum(confirmed_cases) as confirmed_cases, sum(deaths) as deaths
        from bigquery-public-data.covid19_usafacts.summary
        group by state,date
        """

        self.output_dir = output_dir
        self.file_dir = file_dir
        self.new_data = dict()
        self.cases_data = 0

    def dump_to_js(self):
        js_dumper = JSDumper(file_dir=self.file_dir, new_data=self.new_data, cases_data=self.cases_data,
                             output_dir=self.output_dir)
        js_dumper.dump()
        return self

    def get_areas_data(self):
        areas_data = {key: None for key in self.location_dict}
        for id, location_abbr in self.location_dict.items():
            # print(id)
            # print(location_abbr)
            # self.bqclient.query("""
            #     UPDATE `hashtag_dataset.hashtags{}`
            #     SET hashtags="#covid19"
            #     WHERE hashtags="#COVID__19"
            # """.format(location_abbr))
            areas_data[id] = self._get_one_area_data(location_abbr)
        self.new_data = areas_data

    def _get_one_area_data(self, area_abbr):
        query_string = self.query_string.format(area_abbr)
        dataframe = (
            self.bqclient.query(query_string)
                .result()
                .to_dataframe()
        )
        return dataframe

    def get_cases_deaths(self):
        query_string = self.query_string2
        dataframe = (
            self.bqclient.query(query_string)
                .result()
                .to_dataframe()
        )
        self.cases_data = dataframe


class TweetsServer:
    def __init__(self, json_filename):
        self.ACCESS_TOKEN = '1180268654501535747-aDzXWydfhkQd9LMt078S2WYblaQ5Au'  # your access token
        self.ACCESS_SECRET = 'PVGrqgKkG0MYcRXyDRi117bOpguEHkVJZY04NGILXzt8W'  # your access token secret
        self.CONSUMER_KEY = 'eBwobMTGCxsZtLXHgP1UIYk25'  # your API key
        self.CONSUMER_SECRET = 'ZeatKOobNhWfP7rfX697KdExWcLCr4rYYHN6hdfNsIKYqqxMYQ'  # your API secret key
        self.auth = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
        self.auth.set_access_token(self.ACCESS_TOKEN, self.ACCESS_SECRET)
        self.json_filename = json_filename

    def get_tweets_ids(self):
        tmp_list = []
        with open(self.json_filename) as f:
            pop_data = json.load(f)
            for i in range(52):
                for k, v in pop_data['features'][i]['properties']['topics'].items():
                    tmp_list.append(k)
                    break

        api = tweepy.API(auth_handler=self.auth, parser=JSONParser(), wait_on_rate_limit=True)
        tmp_dict = collections.defaultdict(list)

        for i in range(52):
            query = tmp_list[i]
            result = api.search(q=query, count=10)["statuses"]
            for tweets_info in result:
                tmp_dict[i].append(tweets_info['id_str'])

        for k, v in tmp_dict.items():
            pop_data['features'][k]['properties']['tweets_id'] = v
        res = []
        for t in pop_data["features"]:
            res.append(json.dumps(t))

        with open(self.json_filename, "w") as resfile:
            resfile.write('var testData2 = {"type":"FeatureCollection","features":[')
            for r in res:
                resfile.write('\n' + r + ',')
            resfile.write('\n]};')


class DataServer:
    def __init__(self, location_dict, js_file, output_file):
        self.location_dict = location_dict
        self.js_file = js_file
        self.output_file = output_file
        self.big_query_reader = BigQueryReader(location_dict=self.location_dict,
                                               file_dir=self.js_file,
                                               output_dir=self.output_file)
        self.tweets_server = TweetsServer(json_filename=self.output_file)

    def fetch_onces(self):
        print("get cases / deaths data...")
        self.big_query_reader.get_cases_deaths()

        print("get sub-topics for every states...")
        self.big_query_reader.get_areas_data()
        self.big_query_reader.dump_to_js()

        print("get example twitter ids for sub-topics...")
        self.tweets_server.get_tweets_ids()
        print("finished, result to {}".format(self.output_file))

# helper function
def convert_to_js(file_dir):
    tmp = []
    with open(file_dir, 'r') as file:
        tmp = file.readlines()
    with open(file_dir, 'w+') as file:
        file.write("var statesData = ")
        for row in tmp:
            file.write(row)
        file.write(";")

def main():
    js_file = "us-states.js"
    output_file = "new-us-states.js"

    # Read abbreviation list of all states
    location_data = []
    with open('US_locations.csv') as location_file:
        reader = csv.reader(location_file, delimiter=',')
        for line in reader:
            location_data.append(line)

    location_abbr_list = [location[1] for location in location_data]
    location_id_list = [location[6] for location in location_data]
    location_dict = dict(zip(location_id_list, location_abbr_list))

    data_server = DataServer(location_dict=location_dict, js_file=js_file, output_file=output_file)
    data_server.fetch_onces()

if __name__ == "__main__":
    main()
