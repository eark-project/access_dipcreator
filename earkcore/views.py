import os
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import login_required
from config.params import config_path_work
from config.params import config_path_reception

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseBadRequest

from earkcore.models import InformationPackage
from earkcore.utils.fileutils import read_file_content
from earkcore.filesystem.fsinfo import fsize, get_mime_type
from config.params import config_max_filesize_viewer
import base64
from django.template import RequestContext, loader
import json
from earkcore.filesystem.fsinfo import path_to_dict
from django.http import JsonResponse


class InformationPackageDetailView(DetailView):
    model = InformationPackage
    template_name = 'earkcore/ip_detail.html'

@login_required
@csrf_exempt
def check_folder_exists(request, folder):
    path = os.path.join(config_path_work, folder)
    return HttpResponse(str(os.path.exists(path)).lower())

@login_required
@csrf_exempt
def check_submission_exists(request, packagename):
    # submission already exists, if a delivery XML is in the reception folder
    path = os.path.join(config_path_reception, ("%s.xml" % packagename))
    return HttpResponse(str(os.path.exists(path)).lower())

@login_required
def working_area(request, section, uuid):
    template = loader.get_template('earkcore/workingarea.html')
    request.session['uuid'] = uuid
    def f(x):
        return {
            'sip2aip': "SIP to AIP conversion",
            'sipcreation': "SIP creation",
            'aip2dip': "AIP to DIP conversion",
        }[x]
    context = RequestContext(request, {
        "title": f(section),
        "section": section,
        "uuid": uuid,
        "dirtree": json.dumps(path_to_dict('/var/data/earkweb/work/'+uuid, strip_path_part=config_path_work), indent=4, sort_keys=False, encoding="utf-8")
    })
    return HttpResponse(template.render(context))

@login_required
@csrf_exempt
def read_ipfc(request, ip_sub_file_path):
    # only allow reading from session working directory (ip_sub_file_path must begin with uuid)
    file_path = os.path.join(config_path_work, ip_sub_file_path)
    if not os.path.exists(file_path):
        return HttpResponseNotFound("File not found %s vs %s" % (ip_sub_file_path, file_path))
    elif not os.path.isfile(file_path):
        return HttpResponseBadRequest("Not a file")
    else:
        file_size = fsize(file_path)
        if file_size <= config_max_filesize_viewer:
            file_content = read_file_content(file_path)
            mime = get_mime_type(file_path)
            if get_mime_type(file_path) == "image/png" or get_mime_type(file_path) == "image/jpg":
                file_content = "data:"+mime+";base64,"+base64.b64encode(file_content)
            return HttpResponse(file_content)
        else:
            return HttpResponseForbidden("Size of requested file exceeds limit (file size %d > %d)" % (file_size, config_max_filesize_viewer))


@login_required
@csrf_exempt
def get_directory_json(request):
    uuid = request.POST['uuid']
    directory = '/var/data/earkweb/work/'+uuid+'/'
    dirlist = os.listdir(directory)
    if len(dirlist) > 0:
        package_name = dirlist[0]
    else:
        package_name = dirlist
    return JsonResponse({ "data": path_to_dict('/var/data/earkweb/work/'+uuid, strip_path_part=config_path_work+'/') })