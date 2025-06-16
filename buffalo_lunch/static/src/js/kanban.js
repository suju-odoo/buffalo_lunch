/** @odoo-module */
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { useService } from "@web/core/utils/hooks";
import { SurveyKanbanRenderer } from '@survey/views/survey_views';

export class BuffaloSurveyKanbanRenderer extends SurveyKanbanRenderer {}

export class BuffaloSurveyKanbanController extends KanbanController {
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

registry.category("views").add("buffalo_survey_view_kanban", {
    ...kanbanView,
    Renderer: BuffaloSurveyKanbanRenderer,
    Controller: BuffaloSurveyKanbanController,
    buttonTemplate: "buffalo_lunch.KanbanView.Buttons",
});
