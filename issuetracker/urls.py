from django.contrib import admin
from django.urls import path

from issuetracker.views import (
    issue_detail,
    issue_list,
    message_list,
    search_issues,
    search_messages,
)

app_name = "issues"

urlpatterns = [
    path("issues/", issue_list, name="issue_list"),
    path("messages/", message_list, name="message_list"),
    path("messages/search/", search_messages, name="search_messages"),
    path("issues/search/", search_issues, name="search_issues"),
    path("issue/<int:issue_id>/", issue_detail, name="issue_detail"),
]
