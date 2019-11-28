# -*- coding: utf-8 -*-
"""
    emmett.routing.rules
    --------------------

    Provides routing rules definition apis.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import os

from ..cache import RouteCacheRule
from ..http import HTTPResponse
from ..pipeline import Pipeline, Pipe
from .routes import HTTPRoute, WebsocketRoute


class RoutingRule:
    @property
    def app(self):
        return self.router.app

    def build_name(self, f):
        filename = os.path.realpath(f.__code__.co_filename)
        short = filename[1 + len(self.app.root_path):].rsplit('.', 1)[0]
        if not short:
            short = filename.rsplit('.', 1)[0]
        if short == "__init__":
            short = self.app.root_path.rsplit('/', 1)[-1]
        # allow only one level of naming if name is builded
        if len(short.split(os.sep)) > 1:
            short = short.split(os.sep)[-1]
        return '.'.join(short.split(os.sep) + [f.__name__])


class HTTPRoutingRule(RoutingRule):
    __slots__ = (
        'router', 'name', 'f', 'output_type',
        'paths', 'schemes', 'methods', 'hostname', 'prefix',
        'template', 'template_folder', 'template_path',
        'pipeline', 'pipeline_flow_open', 'pipeline_flow_close',
        'response_builders', 'cache_rule'
    )

    def __init__(
        self, router, paths=None, name=None, template=None, pipeline=None,
        injectors=None, schemes=None, hostname=None, methods=None, prefix=None,
        template_folder=None, template_path=None, cache=None, output='auto'
    ):
        self.router = router
        self.name = name
        self.paths = paths
        if self.paths is None:
            self.paths = []
        if not isinstance(self.paths, (list, tuple)):
            self.paths = (self.paths,)
        self.schemes = schemes or ('http', 'https')
        if not isinstance(self.schemes, (list, tuple)):
            self.schemes = (self.schemes,)
        self.methods = methods or ('get', 'post', 'head')
        if not isinstance(self.methods, (list, tuple)):
            self.methods = (self.methods,)
        self.hostname = hostname or self.app.config.hostname_default
        if prefix:
            if not prefix.startswith('/'):
                prefix = '/' + prefix
        self.prefix = prefix
        if output not in self.router._outputs:
            raise SyntaxError(
                'Invalid output specified. Allowed values are: {}'.format(
                    ', '.join(self.router._outputs.keys())))
        self.output_type = output
        self.template = template
        self.template_folder = template_folder
        self.template_path = template_path or self.app.template_path
        self.pipeline = (
            self.router.pipeline + (pipeline or []) +
            self.router.injectors + (injectors or []))
        self.cache_rule = None
        if cache:
            if not isinstance(cache, RouteCacheRule):
                raise RuntimeError(
                    'route cache argument should be a valid caching rule')
            if any(key in self.methods for key in ['get', 'head']):
                self.cache_rule = cache
        # check pipes are indeed valid pipes
        if any(not isinstance(pipe, Pipe) for pipe in self.pipeline):
            raise RuntimeError('Invalid pipeline')

    def __call__(self, f):
        if not self.paths:
            self.paths.append("/" + f.__name__)
        if not self.name:
            self.name = self.build_name(f)
        # is it good?
        if self.name.endswith("."):
            self.name = self.name + f.__name__
        #
        if not self.template:
            self.template = f.__name__ + self.app.template_default_extension
        if self.template_folder:
            self.template = os.path.join(self.template_folder, self.template)
        pipeline_obj = Pipeline(self.pipeline)
        wrapped_f = pipeline_obj(f)
        self.pipeline_flow_open = pipeline_obj._flow_open()
        self.pipeline_flow_close = pipeline_obj._flow_close()
        self.f = wrapped_f
        output_type = pipeline_obj._output_type() or self.output_type
        self.response_builders = {
            method.upper(): self.router._outputs[output_type](self)
            for method in self.methods
        }
        if 'head' in self.response_builders:
            self.response_builders['head'].http_cls = HTTPResponse
        for idx, path in enumerate(self.paths):
            self.router.add_route(HTTPRoute(self, path, idx))
        return f


class WebsocketRoutingRule(RoutingRule):
    __slots__ = (
        'router', 'name', 'f', 'output_type',
        'paths', 'schemes', 'hostname', 'prefix'
    )

    def __init__(
        self, router, paths=None, name=None, pipeline=None, schemes=None,
        hostname=None, prefix=None, output='auto'
    ):
        self.router = router
        self.name = name
        self.paths = paths
        if self.paths is None:
            self.paths = []
        if not isinstance(self.paths, (list, tuple)):
            self.paths = (self.paths,)
        self.schemes = schemes or ('ws', 'wss')
        if not isinstance(self.schemes, (list, tuple)):
            self.schemes = (self.schemes,)
        self.hostname = hostname or self.app.config.hostname_default
        if prefix:
            if not prefix.startswith('/'):
                prefix = '/' + prefix
        self.prefix = prefix
        # if output not in self.router._outputs:
        #     raise SyntaxError(
        #         'Invalid output specified. Allowed values are: {}'.format(
        #             ', '.join(self.router._outputs.keys())))
        self.output_type = output
        # self.pipeline = self.router.pipeline + (pipeline or [])
        self.pipeline = pipeline or []
        # check pipes are indeed valid pipes
        # if any(not isinstance(pipe, Pipe) for pipe in self.pipeline):
        #     raise RuntimeError('Invalid pipeline')

    def __call__(self, f):
        if not self.paths:
            self.paths.append("/" + f.__name__)
        if not self.name:
            self.name = self.build_name(f)
        # is it good?
        if self.name.endswith("."):
            self.name = self.name + f.__name__
        #
        # pipeline_obj = Pipeline(self.pipeline)
        # wrapped_f = pipeline_obj(f)
        # self.pipeline_flow_open = pipeline_obj._flow_open()
        # self.pipeline_flow_close = pipeline_obj._flow_close()
        # self.f = wrapped_f
        self.f = f
        # output_type = pipeline_obj._output_type() or self.output_type
        # self.response_builders = {
        #     method.upper(): self.router._outputs[output_type](self)
        #     for method in self.methods
        # }
        for idx, path in enumerate(self.paths):
            self.router.add_route(WebsocketRoute(self, path, idx))
        return f