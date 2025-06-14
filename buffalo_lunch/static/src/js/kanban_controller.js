/** @odoo-module */
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { useService } from "@web/core/utils/hooks";

export class BuffaloLunchKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async onNewLunchSurvey() {
        try {
            await this.orm.call("survey.survey", "create_next_lunch_survey")
        }
        catch (error) {
            // legends never fail
        }
    }
}
registry.category("views").add("buffalo_lunch_kanban", {
    ...kanbanView,
    Controller: BuffaloLunchKanbanController,
    buttonTemplate: "buffalo_lunch.KanbanView.Buttons",
});
