#!/usr/bin/env python
import time
import apicurioregistryclient
import traceback
import json
import requests
import os
import re
import yaml
from apicurioregistryclient.api import artifacts_api, metadata_api, artifact_rules_api

def extract(systemName):
    print(f"INFO: Extracting values from '{systemName}/info.yaml'")

    with open(f"{systemName}/info.yaml") as file:
        yaml_file = yaml.safe_load(file)
        smc = yaml_file.get('systemName')
        schemas = yaml_file.get('schemas')
        length = len(schemas)
        msg = ''
        for index in range(length):
            print(f"INFO: Extracting schema '{schemas[index].get('name')}'")
            id = uploadSchema(smc, schemas[index].get('type'), schemas[index].get('name'),
                              schemas[index].get('description'), schemas[index].get('version'),
                              schemas[index].get('url'), schemas[index].get('labels'),schemas[index].get('compatibilityRule'))
            #appending the id returned from uploadSchema()
            msg+= id + '</br>'

def uploadSchema(groupID, type, artifactName, schemaDescription, schemaVersion, url, labels, rules):
    #connecting with the Registry API based on client ID and Secret
    configuration = apicurioregistryclient.Configuration(
      host=os.environ['URL'],
      username=os.environ['ID'],
      password=os.environ['SECRET']
    )
    token = 'Bearer ' + os.environ['TOKEN']

    #accessing the client provided GitHub API and converting the Response Object to JSON
    schemaObject = requests.get(url, headers={'Authorization': token}).json()
    #extracting the schemas from the raw GitHub uri
    schemaJson = json.loads(requests.get(schemaObject["download_url"]).content)

    schemaSize = schemaObject["size"]
    if schemaSize/1024 > 64:
        raise Exception(f"ERROR: Schema to be uploaded exceeds the allowed schema size of 64KB.")

    id = artifactName.title().replace(" ", "") + "." + type.lower()
    schemaJson["$id"] = os.environ['URL'] + '/groups/' + groupID + '/artifacts/' + id + '/versions/' + schemaVersion
    schemaRegistryUrl = os.environ['URL'] + '/artifacts/' + groupID + '/' + id + '/versions/' + schemaVersion

    retry_count = 0
    max_retries = 2
    retry_interval = 2 # seconds
    while retry_count < max_retries:
        try:
            api_instance = artifacts_api.ArtifactsApi(apicurioregistryclient.ApiClient(configuration))
            result = api_instance.create_artifact(groupID, json.dumps(schemaJson),
                                                  x_registry_version=schemaVersion,
                                                  x_registry_artifact_id=id,
                                                  x_registry_artifact_type=type,
                                                  x_registry_name=artifactName,
                                                  x_registry_description=schemaDescription,
                                                  if_exists='RETURN_OR_UPDATE',
                                                  _content_type="application/binary"
                                                  )
            print(f"INFO: Successfully uploaded " + result["id"] + " schema")
            if labels:
                print(f"INFO: Adding the labels.")
                metadata_instance = metadata_api.MetadataApi(apicurioregistryclient.ApiClient(configuration))
                metadata_instance.update_artifact_meta_data(groupID, id,
                                                            editable_meta_data={
                                                                'name':artifactName,
                                                                'description':schemaDescription,
                                                                'labels': labels,
                                                            },
                                                            _content_type="application/json"
                                                            )
            if rules:
                print(f"INFO: Adding the Artifact Compatibility Rule.")
                rules_instance = artifact_rules_api.ArtifactRulesApi(apicurioregistryclient.ApiClient(configuration))
                rules_instance.create_artifact_rule(groupID, id,
                                                    rule={
                                                        'type':'COMPATIBILITY',
                                                        'config':rules,
                                                    },
                                                    _content_type="application/json"
                                                    )
            msg = '\n' + result["id"] + ' schema is available at: ' + schemaRegistryUrl + '\n \n'
        #except requests.exceptions.RequestException as err:
        except apicurioregistryclient.exceptions.ApiException as err:
            print(err)
            if err.status == 409:
                # rate limit reached, wait 2 seconds and try again
                time.sleep(retry_interval)
                retry_count += 1
                print("From if block within exceptions")
            else:
                # another error, throw the exception
                raise err
            traceback.print_exc()
        #print("ERROR: Error occurred" + err)
        return msg

systemNames = [item.name for item in os.scandir('.') if item.is_dir() and re.search('^[A-Z]{3,}$', item.name)]

for systemName in systemNames:
    #if f"{systemName}/info.yaml" in os.environ['MODIFIED_FILES']:
        extract("HETAL")
    #else:
     #   print(f"Skipping '{systemName}/info.yaml' as it was not changed")
