from jinja2 import Environment
from jinja2 import FileSystemLoader
import os
import requests

DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
JSON_TEMPLATES = Environment(loader=FileSystemLoader(DIR_PATH + '/json_templates'))

# Disable https warnings
requests.packages.urllib3.disable_warnings()


class ExampleController:
    url = ""

    def makeCall(self, p_url, method, data=""):
        cookies = {}
        if method == "POST":
            response = requests.post(self.url + p_url, data=data, cookies=cookies, verify=False)
        elif method == "GET":
            response = requests.get(self.url + p_url, cookies=cookies, verify=False)
        if 199 < response.status_code < 300:
            raise Exception("Error: status code" + str(response.status_code))

    def getToken(self, username, password):
        """
        Example of Jinja Template Usage
        :param username:
        :param password:
        :return:
        """
        # Gets the template
        template = JSON_TEMPLATES.get_template('login.j2.json')
        # Creates the payload
        payload = template.render(username=username, password=password)
        # Make the call
        auth = self.makeCall(p_url='/api/aaaLogin.json', data=payload, method="POST").json()
        # Read response
        login_attributes = auth['imdata'][0]['aaaLogin']['attributes']
        # Return data
        return login_attributes['token']
