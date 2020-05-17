import boto3, json
from botocore import UNSIGNED
from botocore.client import Config
from smart_open import open
from elasticsearch import Elasticsearch
from datetime import datetime

def get_matching_s3_keys(bucket, prefix='enigma-jhu/', suffix='json'):
    """
    Generate the keys in an S3 bucket.

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch keys that start with this prefix (optional).
    :param suffix: Only fetch keys that end with this suffix (optional).
    """
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    kwargs = {'Bucket': 'covid19-lake'}

    # If the prefix is a single string (not a tuple of strings), we can
    # do the filtering directly in the S3 API.
    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    while True:
        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp['Contents']:
            key = obj['Key']
            if key.startswith(prefix) and key.endswith(suffix):
                yield key
        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (when this field is missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break

def get_file_url(s3_json_file):
    for file in s3_json_file:
        file_url = 'https://covid19-lake.s3.us-east-2.amazonaws.com/'+file
    return file_url

def get_enigma_jhu_doc(es_doc):
    es_fdoc = {}
    if 'fips' in es_doc.keys():
        es_fdoc['fips'] = str(es_doc['fips'])
    if 'admin2' in es_doc.keys():
        es_fdoc['admin2'] = str(es_doc['admin2'])
    if 'province_state' in es_doc.keys():
        es_fdoc['province_state'] = str(es_doc['province_state'])
    if 'country_region' in es_doc.keys():
        es_fdoc['country_region'] = str(es_doc['country_region'])
    if 'last_update' in es_doc.keys():
        date_time_str = str(es_doc['last_update'])
        es_fdoc['last_update'] = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:%S")
    if 'latitude' in es_doc.keys():
        es_fdoc['latitude'] = float(es_doc['latitude'])
    if 'longitude' in es_doc.keys():
        es_fdoc['longitude'] = float(es_doc['longitude'])
    if 'confirmed' in es_doc.keys():
        es_fdoc['confirmed'] = int(es_doc['confirmed'])
    if 'deaths' in es_doc.keys():
        es_fdoc['deaths'] = int(es_doc['deaths'])
    if 'recovered' in es_doc.keys():
        es_fdoc['recovered'] = int(es_doc['recovered'])
    if 'combined_key' in es_doc.keys():
        es_fdoc['combined_key'] = str(es_doc['combined_key'])
    if 'latitude' in es_doc.keys() and 'longitude' in es_doc.keys():
        es_fdoc['geo_location'] = {
            "lat":float(es_doc['latitude']),
            "lon":float(es_doc['longitude'])
        }
    return es_fdoc

if __name__ == '__main__':
    #es=Elasticsearch([{'host':'localhost','port':9200}])
    es = Elasticsearch(hosts=["localhost"])
    mapping = {
        #"settings": {
        #    "number_of_shards": 2,
        #    "number_of_replicas": 1
        #},
        "mappings": {
            "properties": {
                "fips": {
                    "type": "text"
                },
                "admin2": {
                    "type": "text"
                },
                "province_state": {
                    "type": "text"
                },
                "country_region": {
                    "type": "text"
                },
                "last_update": {     
                    "type": "date",
                    "format": "date_hour_minute_second"
                },
                "latitude": {
                    "type": "float"
                },
                "longitude": {
                    "type": "float"
                },
                "confirmed": {
                    "type": "integer"
                },
                "deaths": {
                    "type": "integer"
                },
                "recovered": {
                    "type": "integer"
                },
                "combined_key": {
                    "type": "keyword"
                },
                "geo_location":{
                    "properties": {
                        "location": {
                            "type": "geo_point"
                        }
                    }
                }
            }
        }
    }
    response = es.indices.create(
        index = "covid19-lake",
        body = mapping,
        ignore = 400 # ignore 400 already exists code
    )
    if 'acknowledged' in response:
        if response['acknowledged'] == True:
            print ("INDEX MAPPING SUCCESS FOR INDEX:", response['index'])
    # catch API error response
    elif 'error' in response:
        print ("ERROR:", response['error']['root_cause'])
        print ("TYPE:", response['error']['type'])

    # print out the response
    print ('\nresponse:', response)

    # Identify raw datafile S3 oblect name
    s3_json_file = get_matching_s3_keys(bucket='covid19-lake', prefix='enigma-jhu/', suffix='json')

    # make URL to access raw json data
    file_url = get_file_url(s3_json_file)
    jhu_docs = open(file_url)
    # read raw data and format document to insert in index
    i = 1
    for line in jhu_docs:
        es_doc = json.loads(line)
        es_fdoc = get_enigma_jhu_doc(es_doc)
        print(es_fdoc['last_update'])
        print(type(es_fdoc['last_update']))
        res = es.index(index='covid19-lake',id=i,body=es_fdoc)
        i = i + 1
        print(res) 











#for line in open('https://covid19-lake.s3.us-east-2.amazonaws.com/enigma-jhu/json/part*.json'):
#    print(repr(line))
#    break

#with smart_open('s3://mybucket/mykey.txt', 'rb') as s3_source:
#    for line in s3_source:
#         print(line.decode('utf8'))
#
#    s3_source.seek(0)  # seek to the beginning
#    b1000 = s3_source.read(1000)  # read 1000 bytes

#https://covid19-lake.s3.us-east-2.amazonaws.com/enigma-jhu/json/part-00000-06b2fec4-7f8e-453f-87ab-865fab0a04df-c000.json
#s3://covid19-lake/enigma-jhu/json/part-00000-06b2fec4-7f8e-453f-87ab-865fab0a04df-c000.json