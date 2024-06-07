# -*- coding: utf-8 -*-
from odoo import http
from werkzeug.wrappers import Response


class Cg1DownloadJson(http.Controller):

#INFO: Este controlador se encarga de generar un archivo de texto con el json generado en la función _cg1_json_generator()
    @http.route('/stock_picking_rest/download_txt/<int:record_id>', type="http", auth='public')
    def index(self, record_id):
        instancia = http.request.env['stock.picking'].browse(record_id)
        content = instancia._cg1_json_generator()
        response = Response(content, mimetype='text/plain')
        filename = f'Pedido {instancia.name}.json'
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response


