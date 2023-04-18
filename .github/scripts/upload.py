#!/usr/bin/env python
import apicurioregistryclient
import json
import requests
import os
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
            url = schemas[index].get('url')
            print(url)            
            print(f"INFO: Extracting schema '{schemas[index].get('name')}'")
            id = uploadSchema(smc, schemas[index].get('type'), schemas[index].get('name'),
                              schemas[index].get('description'), schemas[index].get('version'),
                              schemas[index].get('url'), schemas[index].get('labels'),schemas[index].get('compatibilityRule'))

def uploadSchema(groupID, type, artifactName, schemaDescription, schemaVersion, url, labels, rules):
    #connecting with the Registry API based on client ID and Secret
    configuration = apicurioregistryclient.Configuration(
      host= os.environ['URL'],
      username=os.environ['ID'],
      password=os.environ['SECRET']
    )
    token = 'Bearer ' + os.environ['TOKEN']
    #header = 'Authorization: Bearer ' + os.environ['TOKEN']
    
    #schemaObject = requests.get(url, headers={'Authorization': token}).json()
    schemaObject = requests.get(url).json().content
    #schemaJson = json.loads(requests.get(schemaObject["download_url"]).content)
    schemaJson = json.loads(schemaObject)
    id = artifactName.title().replace(" ", "") + "." + type.lower()
    
    try:
        #label .create
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
        print(result)
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
        print(f"INFO: Successfully uploaded " + result["id"] + " schema")
    except requests.exceptions.RequestException as err:
        print("ERROR: Error occurred" + err)
    return true        
    
extract("HETAL")

