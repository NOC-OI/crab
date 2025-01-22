import requests
from enum import Enum

class HTTPMethod(Enum):
    GET = 1
    POST = 2
    PUT = 3
    DELETE = 4

class Client:
    __max_retries = 3
    __connection_timeout = 3000

    def __init__(self, couch_base_uri):
        if couch_base_uri.endswith("/"):
            couch_base_uri = couch_base_uri[:-1]
        self.__couch_base_uri = couch_base_uri
        self.__current_session = requests.Session()

    def set_timeout(self, timeout):
        self.__connection_timeout = timeout

    def set_max_retries(self, max_retries):
        self.__max_retries = max_retries

    def __couch_query(self, endpoint, method, args = None):
        try_n = 0
        while try_n < self.__max_retries:
            try:
                if method == HTTPMethod.POST:
                    response = self.__current_session.post(self.__couch_base_uri + endpoint, json=args, timeout=self.__connection_timeout)
                elif method == HTTPMethod.DELETE:
                    response = self.__current_session.delete(self.__couch_base_uri + endpoint, timeout=self.__connection_timeout)
                elif method == HTTPMethod.PUT:
                    response = self.__current_session.put(self.__couch_base_uri + endpoint, json=args, timeout=self.__connection_timeout)
                else:
                    response = self.__current_session.get(self.__couch_base_uri + endpoint, timeout=self.__connection_timeout)
                if response.status_code >= 200 and response.status_code < 300:
                    return response.json()
                else:
                    raise RuntimeError("Error code returned from CouchDB (" + str(response.status_code) + ")")
            except ConnectionError:
                print("Request (" + endpoint + ") was refused on try " + str(try_n))
                try_n += 1
            except Timeout:
                print("Request (" + endpoint + ") timed out on try " + str(try_n))
                try_n += 1
        raise ConnectionError("Gave up connecting to CouchDB after " + str(try_n) + " tries")

    def find(self, database, selector = [], fields = None, sort = None, page = 0, page_size = 20):
        for sortby in sort:
            for key in sortby:
                if not key in selector:
                    selector[key] = {"$exists": True}
        mango = {
                "selector": selector,
                "skip": page * page_size,
                "limit": page_size
            }

        if not sort is None:
            mango["sort"] = sort

        if not fields is None:
            mango["fields"] = fields

        return self.__couch_query("/" + database + "/_find", HTTPMethod.POST, mango)

    def get_document(self, database, doc_id):
        return self.__couch_query("/" + database + "/" + str(doc_id), HTTPMethod.GET)

    # This is a utility function - it will just delete whatever is at the ID!
    def delete_document(self, database, doc_id):
        document = self.__couch_query("/" + database + "/" + str(doc_id), HTTPMethod.GET)
        return self.__couch_query("/" + database + "/" + str(doc_id) + "?rev=" + document["_rev"], HTTPMethod.DELETE)

    def put_document(self, database, doc_id, document):
        return self.__couch_query("/" + database + "/" + str(doc_id), HTTPMethod.PUT, document)

    # Another utility function, will modify the document regardless of _rev
    def patch_document(self, database, doc_id, document_diff):
        document = self.__couch_query("/" + database + "/" + str(doc_id), HTTPMethod.GET)
        merged_document = {**document, **document_diff}
        return self.__couch_query("/" + database + "/" + str(doc_id), HTTPMethod.PUT, merged_document)
