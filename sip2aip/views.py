import os
import functools
import json
import tarfile
from threading import Thread
import traceback
import urllib

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.template import RequestContext, loader
from django.utils import timezone
from lxml import etree
import requests
from django.views.generic.detail import DetailView
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from django.contrib.auth.decorators import permission_required, login_required
from earkcore.models import StatusProcess_CHOICES
from django.views.decorators.csrf import csrf_exempt

from earkcore.models import InformationPackage

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from celery.result import AsyncResult
from workers import tasks
from django.http import JsonResponse
from django.forms import ModelChoiceField
from sip2aip import forms
import urllib2
import workers.tasks
from workers.taskconfig import TaskConfig
from workflow.models import WorkflowModules
import json

from config.params import config_path_work
from earkcore.filesystem.fsinfo import path_to_dict

import logging
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def ip_detail_table(request):
    pkg_id = request.POST['pkg_id']
    print pkg_id
    print config_path_work
    context = RequestContext(request, {
        "ip": InformationPackage.objects.get(pk=pkg_id),
        "StatusProcess_CHOICES": dict(StatusProcess_CHOICES),
        "config_path_work": config_path_work
    })
    return render_to_response('sip2aip/iptable.html', locals(), context_instance=context)

@login_required
def index(request):
    template = loader.get_template('sip2aip/index.html')
    context = RequestContext(request, {

    })
    return HttpResponse(template.render(context))

class InformationPackageList(ListView):
    """
    List IngestQueue
    """
    model = InformationPackage
    template_name='sip2aip/reception.html'
    context_object_name='ips'
    queryset=InformationPackage.objects.filter(statusprocess__lt = 9999).filter(statusprocess__gt = 99)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(InformationPackageList, self).dispatch( *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InformationPackageList, self).get_context_data(**kwargs)
        context['StatusProcess_CHOICES'] = dict(StatusProcess_CHOICES)
        return context

@login_required
@csrf_exempt
def get_directory_json(request):
    uuid = request.POST['uuid']
    directory = '/var/data/earkweb/work/'+uuid+'/'
    print "List directory: %s" % directory
    dirlist = os.listdir(directory)
    if len(dirlist) > 0:
        package_name = dirlist[0]
    else:
        package_name = dirlist
    return JsonResponse({ "data": path_to_dict('/var/data/earkweb/work/'+uuid) })

@login_required
def working_area(request, uuid):
    template = loader.get_template('sip2aip/workingarea.html')
    print uuid
    context = RequestContext(request, {
        "uuid": uuid,
        "dirtree": json.dumps(path_to_dict('/var/data/earkweb/work/'+uuid), indent=4, sort_keys=False, encoding="utf-8")
    })
    return HttpResponse(template.render(context))

class InformationPackageDetail(DetailView):
    """
    Submit and View result from checkout to work area
    """
    model = InformationPackage
    context_object_name='ip'
    template_name='sip2aip/detail.html'


    def dispatch(self, *args, **kwargs):
        return super(InformationPackageDetail, self).dispatch( *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InformationPackageDetail, self).get_context_data(**kwargs)
        context['StatusProcess_CHOICES'] = dict(StatusProcess_CHOICES)
        context['form'] = forms.SIPPackageWorkflowModuleSelectForm()
        context['config_path_work'] = config_path_work
        return context

@login_required
def progress(request):
    if 'task_id' in request.session.keys() and request.session['task_id']:
        task_id = request.session['task_id']
    context = RequestContext(request, {
        'form': forms.PackageWorkflowModuleSelectForm()
    })
    return render_to_response('sip2aip/progress.html', locals(), context_instance=context)

@login_required
@csrf_exempt
def apply_workflow(request):
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        print "Workflow execution"
        # selected_ip = request.POST['selected_ip']
        # print "selected_ip: " + request.POST['selected_ip']
        # selected_action = request.POST['selected_action']
        # print "selected_action: " + request.POST['selected_action']
        # if not (selected_ip and selected_action):
        #     return JsonResponse({"success": False, "errmsg": "Missing input parameter!"})
        # wfm = WorkflowModules.objects.get(pk=selected_action)
        # tc = TaskConfig(wfm.expected_status,  wfm.success_status, wfm.error_status)
        # if request.is_ajax():
        #     taskClass = getattr(tasks, wfm.identifier)
        #     print "Executing task: %s" % wfm.identifier
        #     job = taskClass().apply_async((selected_ip, tc,), queue='default')
        #     print "Task identifier: %s" % job.id
        #     data = {"success": True, "id": job.id}
        # else:
        #     data = {"success": False, "errmsg": "not ajax"}
        data = {"success": True, "id": "xyz", "myprop": "val"}
    except:
        tb = traceback.format_exc()
        logger.error(str(tb))
        data = {"success": False, "errmsg": "an error occurred!"}
        return JsonResponse(data)
    return JsonResponse(data)


@login_required
@csrf_exempt
def apply_task(request):
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        selected_ip = request.POST['selected_ip']
        print "selected_ip: " + request.POST['selected_ip']
        selected_action = request.POST['selected_action']
        print "selected_action: " + request.POST['selected_action']
        if not (selected_ip and selected_action):
            return JsonResponse({"success": False, "errmsg": "Missing input parameter!"})
        wfm = WorkflowModules.objects.get(pk=selected_action)
        tc = TaskConfig(wfm.expected_status,  wfm.success_status, wfm.error_status)
        if request.is_ajax():
            taskClass = getattr(tasks, wfm.identifier)
            print "Executing task: %s" % wfm.identifier
            job = taskClass().apply_async((selected_ip, tc,), queue='default')
            print "Task identifier: %s" % job.id
            data = {"success": True, "id": job.id}
        else:
            data = {"success": False, "errmsg": "not ajax"}
    except:
        tb = traceback.format_exc()
        logger.error(str(tb))
        data = {"success": False, "errmsg": "an error occurred!"}
        return JsonResponse(data)
    return JsonResponse(data)

@login_required
@csrf_exempt
def poll_state(request):
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        if request.is_ajax():
            if 'task_id' in request.POST.keys() and request.POST['task_id']:
                task_id = request.POST['task_id']
                task = AsyncResult(task_id)
                if task.state == "SUCCESS":
                    aggr_log = '\n'.join(task.result.log)
                    aggr_err = '\n'.join(task.result.err)
                    data = {"success": True, "result": task.result.success, "state": task.state, "log": aggr_log, "err": aggr_err}
                elif task.state == "PROGRESS":
                    data = {"success": True, "result": task.state, "state": task.state, "info": task.info}
            else:
                data = {"success": False, "errmsg": "No task_id in the request"}
        else:
            data = {"success": False, "errmsg": "Not ajax"}
    except Exception, err:
        data = {"success": False, "errmsg": err.message}
        tb = traceback.format_exc()
        logger.error(str(tb))

    return JsonResponse(data)

