/** @odoo-module **/

import PlanningGanttController from '@planning/js/planning_gantt_controller';
import {_t} from 'web.core';
import {Markup} from 'web.utils';

PlanningGanttController.include({
    events: Object.assign({}, PlanningGanttController.prototype.events, {
        // 'click .o_gantt_button_copy_month': '_onCopyMonthClicked',
        'click .o_gantt_button_copy_month': '_onCopyMonthWzdClicked',
    }),
    buttonTemplateName: 'MonthPlanningGanttView.buttons',

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onCopyMonthClicked(ev) {
        ev.preventDefault();
        const result = await this._rpc({
            model: this.modelName,
            method: 'action_copy_previous_month',
            args: [
                this.model.convertToServerTime(this.model.get().startDate),
                this.model._getDomain(),
            ],
            context: this.context || {},
        });
        if (result) {
            const message = _t("The shifts from the previous week have successfully been copied.");
            this.displayNotification({
                type: 'success',
                message: Markup`<i class="fa fa-fw fa-check"></i><span class="ml-1">${message}</span>`,
            });
        } else {
            this.displayNotification({
                type: 'danger',
                message: _t('There are no shifts to copy or the previous shifts were already copied.'),
            });
        }
        this.reload();

    },
    _onCopyMonthWzdClicked: function (ev) {
        ev.preventDefault();
        var self = this;
        var state = this.model.get();
        let additional_context = _.extend({}, this.context, {
            'default_start_datetime': this.model.convertToServerTime(state.startDate),
            'default_end_datetime': this.model.convertToServerTime(state.stopDate),
            'scale': state.scale,
            'active_domain': this.model.domain,
        });
        return this.do_action('elogia_project.planning_copy_month_action', {
            additional_context: additional_context,
            on_close: function () {
                self.reload();
            }
        });
    },
});