import errno
import json
import os
from typing import Tuple
from pylatex.utils import escape_latex, NoEscape

from .ref_regex import *


def save_as_json(obj: object, path: str) -> None:
    with open(path, "w") as file:
        json.dump(obj, file, indent=2)


def load_json(path: str) -> dict:
    with open(path, "r") as file:
        loaded = json.load(file)
    return loaded


def create_dir_if_necessary(dir_path: str) -> None:
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


def construct_svn_revision_url(revision: str) -> str:
    """
    Extracts a revision ID and constructs a URL to SVN Apache.
    :param revision: Revision to build the URL to
    :return: URL
    """
    revision_id = extract_numbers(revision)[0]
    return "https://svn.apache.org/r{}".format(revision_id)


def extract_references(text: str, project: str) -> Tuple[Set[str], Set[str], Set[str], Set[str], Set[str]]:
    """
    Extract different types of references from the specified text.
    :param text: Text to extract references from
    :param project: Name of the project; helpful for some references extractors
    :return: Tuple of sets containing data in the following format:
        1. URLs without mailing lists and PDF documents URLs
        2. Revisions
        3. Mailing lists
        4. PDF documents URLs
    """
    urls = extract_urls(text, project)
    revisions = extract_revisions(text)

    mailing_lists = filter_mailing_list_urls(urls)
    urls = urls.difference(mailing_lists)

    pdf_documents = filter_pdf_document_urls(urls)
    urls = urls.difference(pdf_documents)

    other_issues = extract_issues(text, project)

    return urls, revisions, mailing_lists, pdf_documents, other_issues


def filter_pdf_document_urls(urls: Set[str]) -> Set[str]:
    """
    Filter URLs leading to PDF documents. Usually, if there is a URL to a PDF document inside discussions, there is a
    high chance that this is a documentation.
    :param urls: List of URLs to filter PDF documents from
    :return: List of PDF document URLS
    """
    return set([url for url in urls if url.endswith(".pdf")])


def filter_mailing_list_urls(urls: Set[str], mailing_list_keys=None) -> Set[str]:
    """
    Filter URLs leading to mailing lists. This is a very rough implementation and should definitely be improved.
    :param urls: List of URLs to filter mailing lists from
    :param mailing_list_keys: If the URL is a mailing list, any entry from this list should be present in the URL.
    Otherwise, it checks whether the url contains "mail-archives" or "markmail".
    :return: List of mailing list URLs
    """
    if not mailing_list_keys:
        mailing_list_keys = ["mail-archives", "markmail"]
    return set([url for url in urls if any(key in url for key in mailing_list_keys)])


def noformat_to_latex(string: str) -> str:
    """
    Convert {noformat} blocks to LaTeX verbatim with line breaking.
    :param string: String to replace noformat at. String should be already parsed by escape_latex
    :return: Formatted string
    """
    while string.find(r"\{noformat\}") != -1:
        string = string.replace(r"\{noformat\}", r"\begin{spverbatim}", 1)
        string = string.replace(r"\{noformat\}", r"\end{spverbatim}\ ", 1)
    return string


def extract_code_listings(string: str, to_latex: bool = True) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Given a string with Atlassian code listings, replaces them with flags and returns a tuple of a string with flags
    and a list of code listings with corresponding flags. This is primarily used to avoid escaping LaTeX characters
    inside listings.
    :param string: String with Atlassian code listings
    :param to_latex: Whether to convert listings to LaTeX format
    :return: Tuple containing two values:
    1. String with all code listings replaced with flags of the form <<!PDFGEN123!>>, where 123 is the serial number
    of a listing
    2. List of tuples, each of which contains two values:
        2.1 Flag
        2.2 Content that is intended to replace the flag in the string
    """
    listings = []
    listing_index = 1
    pattern = re.compile(r"(({code:((?s).*?)})|({code}))((?s).*?){code}")

    while True:
        listing = pattern.search(string)
        if not listing:
            break
        content = listing.group(0)
        key = "<<!PDFGEN{}!>>".format(listing_index)
        listing_index += 1
        string = string.replace(content, key)
        if to_latex:
            language = re.search(r"{code:((?s).*?)}", content)
            if language:
                section = language.group(0)
                language = language.group(1)
                content = content.replace(section, r"\begin{lstlisting}[language=" + language + "]", 1)
            else:
                content = content.replace(r"{code}", r"\begin{lstlisting}", 1)
            content = content.replace(r"{code}", r"\end{lstlisting}\ ", 1)
        if len(content) > 400:
            # If the string length is too, LaTeX throws an error "Dimension too large".
            # Unfortunately, I couldn't find what is the max dimension, so let's say that typical
            # line never exceeds 400 characters, and so, after each 400 characters, a newline character is inserted.
            content = '\n'.join(content[i:i + 400] for i in range(0, len(content), 400))
        listings.append((key, content))
    return string, listings


def escape_with_listings(string: str):
    """
    Escape LaTeX characters except code listings. All Atlassian code listings are converted to the corresponding
    LaTeX ones.
    :param string: String containing text without escaping and with Atlassian code listings
    :return: Formatted string
    """
    string, listings = extract_code_listings(string)
    string = escape_latex(string)
    for listing in listings:
        key, content = listing
        string = string.replace(key, content, 1)
    string = noformat_to_latex(string)
    return NoEscape(string)
