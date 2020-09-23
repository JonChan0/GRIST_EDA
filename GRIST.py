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

    if type(input) == dict:
        length_range = range(1)
    else:
        length_range = range(len(input))

    for i in length_range:

        if type(input) == dict:
            print("The last page has only one entry")
            grantholder = input["Person"]
            institution = input["Institution"]["Name"]
            grant = input["Grant"]

        else:
            grantholder = input[i]["Person"]
            try:
                institution = input[i]["Institution"]["Name"]
            except KeyError:
                pass
            grant = input[i]["Grant"]

        try:
            full_name = grantholder["Title"]  +' '+ grantholder["FamilyName"] + ' ' + grantholder["GivenName"]
        except KeyError:
            try:
                partial_name = grantholder["FamilyName"]+ ' ' + grantholder["GivenName"]
            except KeyError:
                try:
                    partial_name = grantholder["Title"] + ' ' + grantholder["FamilyName"]
                except KeyError:
                    try:
                        partial_name = grantholder["FamilyName"]
                    except KeyError:
                        pass
                except:
                    pass
            except:
                pass
        except:
            pass

        grant_title = grant["Title"]

        try:
            grant_abstract = grant["Abstract"]["$"]
            if re.search(grant_abstract,"\r\n") == True:
                grant_abstract = grant_abstract.replace("\r\n","")
        except KeyError:
            try:
                grant_abstract = grant["Abstract"][0]["$"]
                if re.search(grant_abstract,"\r\n") == True:
                    grant_abstract = grant_abstract.replace("\r\n","")
            except KeyError:
                pass
        except:
            pass


        grant_source = grant["Funder"]["Name"]

        try:
            grant_amount = grant["Amount"]["$"] + grant["Amount"]["@Currency"]
        except KeyError:
            pass


        try:
            start_date = grant["StartDate"]
            end_date = grant["EndDate"]
            grant_type = grant["Type"]
        except KeyError:
            pass

        data_matrix[(page_number-1)*25+i, 0] = str((page_number-1)*25 + i)

        try:
            data_matrix[(page_number-1)*25+i, 1] = full_name
        except UnboundLocalError:
            try:
                data_matrix[(page_number-1)*25+i, 1] = partial_name
            except UnboundLocalError:
                pass
        except:
            pass

        try:
            data_matrix[(page_number-1)*25+i, 2] = institution
        except UnboundLocalError:
            pass

        try:
            data_matrix[(page_number-1)*25+i, 3] = start_date
        except UnboundLocalError:
            pass

        try:
            data_matrix[(page_number-1)*25+i, 4] = end_date
        except UnboundLocalError:
            pass

        data_matrix[(page_number-1)*25+i, 5] = grant_title
        data_matrix[(page_number-1)*25+i, 7] = grant_source

        try:
            data_matrix[(page_number-1)*25+i, 8] = grant_type
        except UnboundLocalError:
            pass

        try:
            data_matrix[(page_number-1)*25+i, 9] = grant_amount
        except UnboundLocalError:
            pass

        try:
            data_matrix[(page_number-1)*25+i, 6] = grant_abstract
        except UnboundLocalError:
            pass

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
        data_matrix = np.empty((no_of_hits, 10), dtype=object)
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

            data_matrix = info_extractor(data_matrix,no_of_hits, page_number, js_extract["RecordList"]["Record"])


        sql_connection.close()
        os.remove(search_term + ".sqlite")

        np.savetxt("output_tsv/" + search_term + ".tsv", data_matrix, fmt="%s", delimiter ="\t", encoding='utf-8')
        print("Numpy array for", search_term, "stored as .tsv")

        break

def main():
    search_time()

main()
