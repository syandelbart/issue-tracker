from django.core.management.base import BaseCommand
import sqlite3
from issuetracker.models import File, Issue, Keyword, Message, Priority, Status, User
import pathlib

import os


class Command(BaseCommand):
    help = "Your command help message"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="roundup",
            help="The source from which the db is coming from, e.g. roundup, jira, etc.",
        )
        parser.add_argument(
            "--sourcefile",
            default="./issuetracker/roundup-old.sqlite3",
            help="The source file to migrate from",
        )

        parser.add_argument(
            "--msg-sourcefile",
            help="The source file to migrate messages from",
        )

        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose mode, this will log all the created & fetched objects",
        )

    def handle(self, *args, **options):
        source = options["source"]
        sourcefile = options["sourcefile"]
        msg_sourcefile = options["msg_sourcefile"]
        verbose = options["verbose"]

        sources = ["roundup", "jira"]

        if source not in sources:
            print(f"Source must be one of {sources}")
            return

        # connect to the old database
        currentdir = pathlib.Path().resolve()

        print("### currentdir: " + currentdir.as_uri())
        print("### sourcefile: " + sourcefile)
        conn = sqlite3.connect(f"{sourcefile}")

        issue_cursor = conn.cursor()
        issue_cursor.execute(
            """
            SELECT
                _issue.id as id,
                _issue._title as title,
                _issue._creator as creator,
                _issue._assignedto as assignedto,
                _issue._creation as creation,
                _issue._activity as latest_activity,
                _issue._status as status,
                _issue._priority as priority
            FROM _issue
            ORDER BY _issue._creation ASC
            """
        )
        issue = issue_cursor.fetchone()
        while issue is not None:
            (
                issue_id,
                title,
                creator,
                assignedto,
                creation,
                latest_activity,
                status,
                priority,
            ) = issue
            created_issue = create_or_get_issue(
                connection=conn,
                id=issue_id,
                title=title,
                creator=creator,
                assignedto=assignedto,
                creation=creation,
                latest_activity=latest_activity,
                status=status,
                priority=priority,
                source=source,
                verbose=verbose,
            )

            file_links = get_links(
                id=created_issue.id,
                connection=conn,
                table="issue_files",
                verbose=verbose,
            )
            message_links = get_links(
                id=created_issue.id,
                connection=conn,
                table="issue_messages",
                verbose=verbose,
            )
            keyword_links = get_links(
                id=created_issue.id,
                connection=conn,
                table="issue_keyword",
                verbose=verbose,
            )

            link_items_to_issue(
                issue=created_issue,
                file_links=file_links,
                message_links=message_links,
                keyword_links=keyword_links,
                source=source,
                msg_sourcefile=msg_sourcefile,
                conn=conn,
                verbose=verbose,
            )

            issue = issue_cursor.fetchone()

            if not verbose and issue_id % 100 == 0:
                print(f"Created issue {created_issue.id}")

        issue_cursor.close()


def link_items_to_issue(
    issue: Issue,
    *,
    file_links,
    message_links,
    keyword_links,
    source,
    msg_sourcefile,
    conn,
    verbose=False,
):
    for file_link in file_links:
        file_obj = create_or_get_file(
            id=file_link, source=source, connection=conn, verbose=verbose
        )
        issue.files.add(file_obj)

    for message_link in message_links:
        message_obj = create_or_get_message(
            id=message_link,
            msg_sourcefile=msg_sourcefile,
            source=source,
            connection=conn,
            verbose=verbose,
        )
        message_obj.issue = issue
        message_obj.save()

    for keyword_link in keyword_links:
        keyword_obj = create_or_get_keyword(
            id=keyword_link, source=source, connection=conn, verbose=verbose
        )
        issue.keywords.add(keyword_obj)

    if not verbose and issue.id % 100 == 0:
        print(f"Created issue {issue.id}")


def create_or_get_user(id, *, connection, verbose=False):
    if id is None:
        return None

    user = fetch_one_from_query(
        connection,
        "SELECT _address,_realname,_username,_organisation FROM _user WHERE id = ?",
        (id,),
    )
    address, realname, username, organisation = user

    user_obj, created = User.objects.using("default").get_or_create(
        id=id,
        email=address,
        realname=realname,
        username=username,
        organisation=organisation,
    )

    print_log(f"-- Creating user {id}" if created else f"-- Getting user {id}", verbose)

    return user_obj


def create_or_get_issue(
    id,
    title,
    *,
    creator,
    creation,
    assignedto,
    latest_activity,
    status,
    priority,
    source,
    connection,
    verbose=False,
):
    print_log(f"-- Creating issue {id}", verbose)
    # print('### database: ' + Issue._state.db)
    issue_obj, _ = Issue.objects.using("default").get_or_create(
        id=id,
        title=title,
        creator=create_or_get_user(creator, connection=connection),
        assignedto=create_or_get_user(assignedto, connection=connection),
        creation=creation,
        latest_activity=latest_activity,
        status=create_or_get_status(id=status, source=source, connection=connection),
        priority=create_or_get_priority(
            id=priority, source=source, connection=connection
        ),
        source=source,
    )

    return issue_obj


def create_or_get_keyword(id, *, source, connection, verbose=False):
    keyword = fetch_one_from_query(
        connection, "SELECT _name FROM _keyword WHERE id = ?", (id,)
    )
    keyword_obj, created = Keyword.objects.using("default").get_or_create(
        id=id, name=keyword[0], source=source
    )

    print_log(
        f"-- Creating keyword {id}" if created else f"-- Getting keyword {id}", verbose
    )

    return keyword_obj


def create_or_get_message(id, *, msg_sourcefile, source, connection, verbose=False):
    if id is None:
        return None
    try:
        fetched_message = Message.objects.get(id=id, source=source)
    except Message.DoesNotExist:
        fetched_message = None

    if fetched_message is not None:
        print_log(f"-- Getting message {id}", verbose)
        return fetched_message

    print_log(f"-- Creating message {id}", verbose)
    message = fetch_one_from_query(
        connection,
        """
        SELECT _summary, _msg._creator, _msg._creation FROM _msg WHERE _msg.id = ?""",
        (id,),
    )

    # Getting message content
    # Message id stored per 1000 messages in a subdirectory
    message_content = message_get_content(
        id=id, msg_sourcefile=msg_sourcefile, verbose=verbose
    )

    message_obj, _ = Message.objects.using("default").get_or_create(
        id=id,
        summary=message[0],
        creator=create_or_get_user(message[1], connection=connection),
        creation=message[2],
        source=source,
        content=message_content,
    )

    file_links = get_links(id=message_obj.id, connection=connection, table="msg_files")

    for file_link in file_links:
        file_obj = create_or_get_file(
            id=file_link, source=source, connection=connection
        )
        message_obj.files.add(file_obj)

    return message_obj


def message_get_content(id, *, msg_sourcefile, verbose=False):
    if msg_sourcefile is not None:
        sub_dir = int(id / 1000)
        message_file = f"{msg_sourcefile}/{sub_dir}/msg{id}"
        # Only if the file exists we can read it
        if os.path.isfile(message_file):
            with open(message_file, "r") as f:
                return f.read()
    return None


# Should replace all the individual functions
def get_links(id, *, connection, table, verbose=False):
    links_cursor = connection.cursor()
    links_cursor.execute(f"SELECT linkid FROM {table} WHERE nodeid = ?", (id,))
    links = links_cursor.fetchall()
    # I want to return a list of ints instead of tuple
    links = [link[0] for link in links]
    return links


def create_or_get_file(id, *, source, connection, verbose=False):
    print_log(f"-- Creating file {id}", verbose)
    file_query = fetch_one_from_query(
        connection,
        "SELECT _name, _creator, _content, _type FROM _file WHERE id = ?",
        (id,),
    )
    file_obj, _ = File.objects.using("default").get_or_create(
        id=id,
        name=file_query[0],
        creator=file_query[1],
        content=file_query[2],
        type=file_query[3],
        source=source,
    )

    return file_obj


def create_or_get_status(id, *, source, connection, verbose=False):
    if id is None:
        return None
    # Since status is needed for each issue, we can assume that these will be created quickly
    try:
        fetched_status = Status.objects.using("default").get(id=id, source=source)
    except Status.DoesNotExist:
        fetched_status = None
    if fetched_status is not None:
        print_log(f"-- Getting status {id}", verbose)
        return fetched_status

    print_log(f"-- Creating status {id}", verbose)
    file_query = fetch_one_from_query(
        connection, "SELECT _name, _creator FROM _status WHERE id = ?", (id,)
    )
    file_obj, _ = Status.objects.using("default").get_or_create(
        id=id, name=file_query[0], creator=file_query[1], source=source
    )

    return file_obj


def create_or_get_priority(id, *, source, connection, verbose=False):
    if id is None:
        return None
    # Since priority is needed for each issue, we can assume that these will be created quickly
    try:
        fetched_status = Priority.objects.using("default").get(id=id, source=source)
    except Priority.DoesNotExist:
        fetched_status = None
    if fetched_status is not None:
        print_log(f"-- Getting priority {id}", verbose)
        return fetched_status

    print_log(f"-- Creating priority {id}", verbose)
    file_query = fetch_one_from_query(
        connection, "SELECT _name, _creator FROM _priority WHERE id = ?", (id,)
    )
    file_obj, _ = Priority.objects.using("default").get_or_create(
        id=id, name=file_query[0], creator=file_query[1], source=source
    )

    return file_obj


def print_log(input: str, verbose: bool = True):
    if verbose:
        print(input)


def fetch_one_from_query(connection, query: str, params: tuple):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchone()


get_issue_messages_query = """
    SELECT
        _msg.id as message_id,
        _msg._summary as message_summary,
        _msg.creation as message_creation,
        _msg._creator as message_creator,
        _msg._content as message_content,
        _msg._type as message_type,
        _msg._activity as message_activity,
        _file._name
    FROM _issue
    JOIN issue_messages
    ON _issue.id = issue_messages.nodeid
    JOIN _msg
    ON _msg.id = issue_messages.linkid
    JOIN msg_files
    ON msg_files.nodeid = _msg.id
    JOIN _file
    ON _file.id = msg_files.linkid
    WHERE _issue.id = ?
    ORDER by _msg._creation DESC
            """
