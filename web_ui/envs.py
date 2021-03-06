"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
"""

Main access for environmental variables. You will need to restart the app to apply those changes

"""

import os

__author__ = "Santiago Flores Kanter (sfloresk@cisco.com)"


def get_username():
    return os.getenv("USERNAME", "")


def get_password():
    return os.getenv("PASSWORD", "")
