from odoo import models, fields, api
from datetime import datetime, time

class HrLateCategory(models.Model):
    _name = 'hr.late.category'
    name = fields.Char(required=True)
    minutes_from = fields.Float(required=True)
    minutes_to = fields.Float(required=True)

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    late_line_ids = fields.One2many('hr.payslip.late.line','payslip_id',compute="_compute_summary",store=True)
    total_overtime_hours = fields.Float(compute="_compute_summary",store=True)
    total_late_hours = fields.Float(compute="_compute_summary",store=True)

    @api.depends('employee_id','date_from','date_to')
    def _compute_summary(self):
        for slip in self:
            overtime = 0.0
            late_total = 0.0
            data = {}

            if not slip.employee_id:
                continue

            df = datetime.combine(slip.date_from, time.min)
            dt = datetime.combine(slip.date_to, time.max)

            atts = self.env['hr.attendance'].search([
                ('employee_id','=',slip.employee_id.id),
                ('check_in','>=',df),
                ('check_in','<=',dt),
            ])

            cats = self.env['hr.late.category'].search([])

            for att in atts:
                extra = 0.0

                if hasattr(att, 'overtime_status') and att.overtime_status == 'approved':
                    extra = getattr(att, 'validated_overtime_hours', 0.0)

                if not extra:
                    extra = getattr(att, 'worked_extra_hours', 0.0)

                if not extra:
                    extra = getattr(att, 'extra_hours', 0.0)

                if extra > 0:
                    overtime += extra

                elif extra < 0:
                    m = abs(extra) * 60
                    late_total += abs(extra)

                    for c in cats:
                        if c.minutes_from <= m <= c.minutes_to:
                            if c.id not in data:
                                data[c.id] = {'c':0,'m':0}
                            data[c.id]['c'] += 1
                            data[c.id]['m'] += m

            lines = []
            for cid, val in data.items():
                lines.append((0,0,{
                    'category_id': cid,
                    'count': val['c'],
                    'total_minutes': val['m'],
                    'total_hours': round(val['m']/60.0, 2)
                }))

            slip.late_line_ids = [(5,0,0)] + lines
            slip.total_overtime_hours = overtime
            slip.total_late_hours = late_total


class HrPayslipLateLine(models.Model):
    _name = 'hr.payslip.late.line'
    payslip_id = fields.Many2one('hr.payslip')
    category_id = fields.Many2one('hr.late.category')
    count = fields.Integer()
    total_minutes = fields.Float()
    total_hours = fields.Float()
