from django.shortcuts import render, get_object_or_404
from .models import Message, Issue
from django.db.models import Q


def message_list(request):
    messages = Message.objects.using("default").all()
    return render(request, "messages/list.html", {"messages": messages})


def issue_list(request):
    issues = Issue.objects.using("default").all()
    return render(request, "issues/list.html", {"issues": issues})


def search_issues(request):
    query = request.GET.get("q", "")
    if len(query) < 3:
        return render(request, "/issues/search.html")

    issues = Issue.objects.using("default").filter(
        Q(id__startswith=query)
        | Q(title__icontains=query)
        | Q(creator__realname__icontains=query)
    )
    return render(request, "/issues/search.html", {"issues": issues})


def search_messages(request):
    query = request.GET.get("q", "")
    if len(query) < 3:
        return render(request, "/messages/search.html")

    messages = Message.objects.using("default").filter(
        Q(id__startswith=query)
        | Q(summary__icontains=query)
        | Q(creator__realname__icontains=query)
    )
    return render(request, "/messages/search.html", {"messages": messages})


def issue_detail(request, *, issue_id):
    issue = get_object_or_404(Issue, pk=issue_id)

    return render(request, "issues/detail.html", {"issue": issue})
