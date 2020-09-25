""" This is a Python script to take input from user and thus to use the Grants RESTful (Grist) API by Europe PMC to search for grants awarded by funders of
Europe PMC notably: BBSRC; CRUK; NIHR; ERC; MRC; Wellcome Trust; WHO and more (see:https://europepmc.org/Funders/)

N.B When inputting search term, if you want to search by specific parameters e.g grant_agency; title; PI; affiliation etc. (see https://europepmc.org/GristAPI)
then you need to input the specific parameters yourself

N.B If you want to use multiple parameters to specify search, input search term with space between each parameter.
"""
import urllib.request, urllib.parse, urllib.error
import json
import sqlite3
import math
import numpy as np
import os
import re

def info_extractor(data_matrix,no_of_hits, page_number, input):


    # In this case, input represents each Record i.e the list or dictionary of js_extract["RecordList"]["Record"]

    if type(input) == dict: # This is the case for where there is only one entry in a page, whereby the type goes to a dictionary, instead of a list of dictionaries.
        length_range = range(1)
    else:
        length_range = range(len(input))

    for i in length_range:

        if type(input) == dict:
            print("The last page has only one entry")
            grantholder = input["Person"]
            institution = input["Institution"]
            grant = input["Grant"]

        else:
            grantholder = input[i]["Person"]
            grant = input[i]["Grant"]

            try: # The try & except clauses reflect the fact that some data is missing for some of the fields.
                institution = input[i]["Institution"]
            except KeyError:
                institution= None

        try:
            full_name = grantholder["Title"]  +' '+ grantholder["GivenName"] + ' ' + grantholder["FamilyName"]
        except KeyError:
            try:
                full_name = grantholder["GivenName"]+ ' ' + grantholder["FamilyName"]
            except KeyError:
                try:
                    full_name = grantholder["Title"] + ' ' + grantholder["FamilyName"]
                except KeyError:
                    try:
                        full_name = grantholder["FamilyName"]
                    except KeyError:
                        full_name = None

        grant_title = grant["Title"]
        grant_source = grant["Funder"]["Name"]

        if institution is not None:
            try:
                institution_name = institution["Name"]
            except KeyError:
                institution_name = None

            try:
                institution_department = institution["Department"]
            except KeyError:
                institution_department = None

        # print((page_number-1)*25+i) # Uncomment if you need to track which record is causing an error

        try:
            grant_abstract = grant["Abstract"]["$"]
        except (KeyError, TypeError):
            try:
                grant_abstract = grant["Abstract"][0]["$"] #This is for the cases where there are two abstracts, one scientific which we pull out, and one for laypeople.
            except (KeyError):
                grant_abstract=None

        if grant_abstract is not None and re.search("\r\n", grant_abstract) is not None:
            grant_abstract = re.sub("\r\n"," ", grant_abstract)

        if grant_abstract is not None and re.search("\t", grant_abstract) is not None:
            grant_abstract = re.sub("\t"," ", grant_abstract)

        if grant_abstract is not None and re.search("\\\\", grant_abstract) is not None:
            grant_abstract = re.sub("\\\\"," ", grant_abstract)

        try:
            grant_amount = grant["Amount"]["$"] + " " + grant["Amount"]["@Currency"]
        except KeyError:
            grant_amount = None


        try:
            start_date = grant["StartDate"]
        except KeyError:
            start_date = None
        try:
            end_date = grant["EndDate"]
        except KeyError:
            end_data = None
        try:
            grant_type = grant["Type"]
        except KeyError:
            grant_type = None



        data_matrix[(page_number-1)*25+i, 0] = str((page_number-1)*25 + i)

        try:
            data_matrix[(page_number-1)*25+i, 1] = full_name
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 1] = None

        try:
            data_matrix[(page_number-1)*25+i, 2] = institution_name
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 2] = None

        try:
            data_matrix[(page_number-1)*25+i, 3] = institution_department
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 3] = None

        try:
            data_matrix[(page_number-1)*25+i, 4] = start_date
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 4] = None

        try:
            data_matrix[(page_number-1)*25+i, 5] = end_date
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 5] = None

        data_matrix[(page_number-1)*25+i, 6] = grant_title

        try:
            data_matrix[(page_number-1)*25+i, 7] = grant_abstract
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 7] = None

        data_matrix[(page_number-1)*25+i, 8] = grant_source

        try:
            data_matrix[(page_number-1)*25+i, 9] = grant_type
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 9] = None

        try:
            data_matrix[(page_number-1)*25+i, 10] = grant_amount
        except UnboundLocalError:
            data_matrix[(page_number-1)*25+i, 10] = None

    return data_matrix

def search_time():
    base_url = "http://www.ebi.ac.uk/europepmc/GristAPI/rest/get/query="
    result_addon_url = "&format=json&resultType=core"

    while True:
        search_term = input("Please enter your search term:")
        if len(search_term) < 1:
            break

        full_url= base_url + urllib.parse.quote(search_term) + result_addon_url

        print("Retrieving", full_url)
        connection = urllib.request.urlopen(full_url)
        data = connection.read().decode()
        print('Retrieved', len(data), 'characters')

        try:
            js = json.loads(data)
        except:
            print(data) # In case Unicode causes error
            continue

        no_of_hits = int(js["HitCount"])
        print("Total number of hit results =", no_of_hits)
        no_of_pages = math.ceil(int(no_of_hits) / 25)

        print("Total number of pages = ", str(no_of_pages))

        if no_of_hits == 0:
            break

# Here is the break-off to save the json files for each page to SQLite3 database.
        sql_connection = sqlite3.connect(search_term + ".sqlite")
        cursorObj = sql_connection.cursor()
        cursorObj.execute('''CREATE TABLE IF NOT EXISTS jsons (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
        json TEXT
        )''' )

        for i in range(1,no_of_pages+1):
            page_addon = "&page=" + str(i)
            full_page_url = full_url= base_url + urllib.parse.quote(search_term) + result_addon_url + page_addon

            print("Retrieving Page", str(i))
            connection = urllib.request.urlopen(full_page_url)
            page_data = connection.read().decode()
            print('Retrieved', len(page_data), 'characters')

            cursorObj.execute('''INSERT INTO jsons (json) VALUES (?)''', [page_data] )


        sql_connection.commit()

# Now we need to analyse each json file and strip out relevant details + store in Numpy array with dtype= strings
# First initialise a empty Numpy array of row length = number of hits & column Length = 10
        data_matrix = np.empty((no_of_hits, 11), dtype=object)
        cursorObj.execute(''' SELECT*FROM jsons''')
        rows = cursorObj.fetchall()

        for row in rows:
            try:
                js_extract = json.loads(row[1])
                print("json file extracted successfully")
            except:
                print("error in extracting json file from SQLite3")
                continue

            page_number = int(js_extract["Request"]["Page"]) # i.e page number = id number in SQLite database representing which json file

            data_matrix = info_extractor(data_matrix,no_of_hits, page_number, js_extract["RecordList"]["Record"]) # Note that each time the request is run, the order of grants returned is changed and may be reflected in differences between .tsv and apparent .json.


        sql_connection.close()
        os.remove(search_term + ".sqlite")

        np.savetxt("output_tsv/" + search_term + ".tsv", data_matrix, fmt="%s", delimiter ="\t", encoding='utf-8')
        print("Numpy array for", search_term, "stored as .tsv")

        break

def main():
    search_time()

main()
