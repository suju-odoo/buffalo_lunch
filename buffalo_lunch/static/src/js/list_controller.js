/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class BuffaloLunchListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async onNewLunchSurvey() {
        try {
            const act_window = await this.orm.call("survey.survey", "open_next_lunch_survey_form")
            this.actionService.doAction(act_window)
        }
        catch (error) {
            // legends never fail
        }
    }
}
registry.category("views").add("buffalo_lunch_list", {
    ...listView,
    Controller: BuffaloLunchListController,
    buttonTemplate: "buffalo_lunch.ListView.Buttons",
});
