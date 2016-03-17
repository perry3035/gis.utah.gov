import gspread
import sys
import re
from collections import OrderedDict
from json import load, dumps
from os import rename
from os.path import join, dirname
from oauth2client.service_account import ServiceAccountCredentials


def munge_data(item, i, indices):
    names = item[indices['layer']].split('.')
    if len(names) == 1:
        category = None
        name = names[0]
    elif len(names) == 2:
        category = names[0].lower()
        name = names[1]
    elif len(names) == 3:
        category = names[0].lower()
        name = '.'.join([names[1], names[2]])

    def utf8_encode(value):
        if value is None:
            return ''

        return value.encode('utf-8')

    def should_link(value):
        if value is None or len(value) == 0:
            return ''

        url = item[indices['url']]
        if url is None or len(url) == 0 or url == 'N/A':
            return utf8_encode(value)

        if url.lower().startswith('http'):
            return '<a href="{}">{}</a>'.format(url, utf8_encode(value))

        return '<a href="{{{{ "/{}" | prepend: site.baseurl }}}}">{}</a>'.format(url, utf8_encode(value))

    def endpoint_link(value):
        if value is None or len(value) == 0:
            return ''

        if ',' in value:
            value = value.split(',')

            return ''.join('<a href="{}" class="pull-right"><i class="fa fa-mixcloud fa-fw" alt="service endpoint"></i></a>'.format(value))

        return '<a href="{}" class="pull-right"><i class="fa fa-mixcloud fa-fw" alt="service endpoint"></i></a>'.format(value)

    return OrderedDict([
        # ('type', utf8_encode(item[indices['data_type']])),
        ('category', utf8_encode(category)),
        ('name', should_link(name.replace('_', ' '))),
        ('agency', utf8_encode(item[indices['data_source']])),
        ('description', utf8_encode(item[indices['description']])),
        ('service', endpoint_link(item[indices['endpoint']]))
    ])

def get_sheet_data(gc, sheet_id, worksheet_id):
    worksheet = gc.open_by_key(sheet_id).worksheet(worksheet_id)

    data = worksheet.get_all_values()

    header = data.pop(0)
    indices = {
        'layer': header.index('SGID Data Layer'),
        'description': header.index('Description'),
        'data_source': header.index('Data Source'),
        'url': header.index('Website URL'),
        'data_type': header.index('Data Type'),
        'endpoint': header.index('Endpoint')
    }

    return [munge_data(item, i, indices) for i, item in enumerate(data)]

def create(data):
    categories = list(set([x['category'] for x in data]))
    categories.sort()
    html = '''---
layout: page
status: publish
title: SGID Index
permalink: /data/sgid-index
---
<script src="{{{{ "/bower_components/list.js/dist/list.js" | prepend: site.baseurl }}}}"></script>
<span id='show_filters' class='pointer'>Show Filters</span>
<div id='filters' class='hidden'>{}</div>
<div id='table' class='datatable'>
    <input class="search" placeholder="Search Data" />
    <table>
    '''.format(' | '.join(['<a id="filter_{0}">{0}</a>'.format(x) for x in categories if len(x) > 0]))

    once = True
    for item in data:
        if once:
            html += '''
        <thead>
            <tr>
{}
            </tr>
        </thead>
        <tbody class='list'>'''.format('\n'.join(['                <th scope="col"><span class="sort" data-sort="{0}">{0}</span></th>'.format(key) for key in item.keys()]))
            once = False
        html += '''
            <tr>
{}
            </tr>'''.format('\n'.join(['                <td data-th="{0}" class="{0}">{1}</td>'.format(key, value) for key, value in item.iteritems()]))
    html += '''
        </tbody>
    </table>
</div>

<script>
    var options = {
    valueNames: [ 'name', 'category', 'agency', 'description' ]
    };

    var filterNode = document.getElementById('filters');
    var togglerNode = document.getElementById('show_filters');
    var datatable = new List('table', options);

    function getParameterByName(name, url) {
        if (!url) {
            url = window.location.href;
        }

        name = name.replace(/[\[\]]/g, "\\$&");
        var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
            results = regex.exec(url);
        if (!results) {
            return null
        };
        if (!results[2]) {
            return '';
        }

        return decodeURIComponent(results[2].replace(/\+/g, " "));
    }

    var category = getParameterByName('category');
    if (category){
        datatable.search(category, ['category']);
    }

    var filterCategories = function(e) {
        if (!e && !e.target) {
            return;
        }

        var clicked = e.target.id;

        var category = clicked.split('_')[1];

        if (category){
            datatable.search(category, ['category']);
        }
    };

    var toggleCategories = function() {
        if ((' ' + filterNode.classList + ' ').indexOf('hidden') >= 0) {
            filterNode.classList.remove('hidden');
            togglerNode.innerHTML = 'Hide Filters';
        } else {
            filterNode.classList.add('hidden');
            togglerNode.innerHTML = 'Show Filters';
        }
    };

    filterNode.addEventListener('click', filterCategories);
    togglerNode.addEventListener('click', toggleCategories);
</script>
'''

    return html

if __name__ == '__main__':
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(join(dirname(__file__), 'gspread-31a626054f8c.json'), scope)

    gc = gspread.authorize(credentials)

    data = get_sheet_data(gc, '11ASS7LnxgpnD0jN4utzklREgMf1pcvYjcXcIcESHweQ', 'SGID Stewardship Info')

    data = filter(lambda x: len(x['name']) > 0, data)
    html = create(data)

    file_path = join(dirname(__file__), '..', 'datatable.html')

    with open(file_path + '.bak', 'wb') as data:
        data.writelines(html)

    rename(file_path + '.bak', file_path)
