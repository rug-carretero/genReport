import os
import errno

from jira.client import JIRA
from jira.resources import Issue

import utils

PROJECTS = ["PDFBOX"]
APACHE_JIRA_SERVER = "https://issues.apache.org/jira/"


class JiraParser:
    def __init__(self, jira_project: str):
        self.jira = JIRA(server=APACHE_JIRA_SERVER)
        self.project = jira_project
        self.__issues = []
        self.__fetch_issues()

    def __fetch_issues(self):
        """
        Fetch all issues from the project and store them in the self.issues list
        """
        issues = []
        block_size = 100
        block_index = 0
        while True:
            start_index = block_index * block_size
            fetched_issues = self.jira.search_issues("project={}".format(self.project), startAt=start_index,
                                                     maxResults=block_size, validate_query=True)
            if len(fetched_issues) == 0:
                break
            block_index += 1
            issues.extend(fetched_issues)
        self.__issues = issues

    def fetch_and_store_comments(self):
        """
        For each issue stored in the JiraParser object,
        fetch all comments and create a JSON file containing necessary information:
        1. Issue key
        2. Date of its creation
        3. Date of its update
        4. List of comments related to the issue:
            4.1. Author of the comment
            4.2. Date of posting the comment
            4.3. Date of updating the comment
            4.4. Body of the comment
        All the data is stored in a file "Projects/<project_name>/Issues/<issue_key>.json"
        """
        for issue in self.__issues:
            filename = issue.raw["key"] + ".json"
            path = os.path.join("Projects", self.project, "Issues", filename)

            if not os.path.exists(os.path.dirname(path)):
                try:
                    os.makedirs(os.path.dirname(path))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
            json_object = self.__prepare_json_object(issue)

            utils.save_as_json(json_object, path)

    def __prepare_json_object(self, issue: Issue):
        """
        Prepare a dictionary containing the following data:
        {
          issue_key: <project name>
          created: <date & time>
          updated: <date & time>
          comments:
          [
            author: <author name>
            created: <date & time>
            updated: <date & time>
            body: <content of comment>
          ]
        }
        :param issue: Issue to retrieve data from
        :return: Dictionary ready to be converted to JSON
        """
        json_object = dict()
        json_object["issue_key"] = issue.raw["key"]
        json_object["created"] = issue.raw["fields"]["created"]
        json_object["updated"] = issue.raw["fields"]["updated"]
        json_object["comments"] = []

        comments = json_object["comments"]

        for comment in self.jira.comments(issue):
            comment_dict = dict()
            comment_dict["author"] = comment.raw["author"]["name"]
            comment_dict["created"] = comment.raw["created"]
            comment_dict["updated"] = comment.raw["updated"]
            comment_dict["body"] = comment.raw["body"]
            comments.append(comment_dict)

        return json_object


if __name__ == "__main__":
    parser = JiraParser(PROJECTS[0])
    parser.fetch_and_store_comments()
