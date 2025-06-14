import re

from . import models


def _process_migration_report(env):
    odoo_versions_to_write_scripts_for = set()
    def _process_disabled_views(html_string):
        odoo_version = _extract_upgrade_version(html_string)
        odoo_versions_to_write_scripts_for.add(odoo_version)
        section_pattern = r'<h3>Disabled views</h3>\s*<ul>(.*?)</ul>'
        section_match = re.search(section_pattern, html_string, re.DOTALL)
        if not section_match:
            return []
        disabled_views_section = section_match.group(1)
        if odoo_version == '18.0':
            view_pattern = r'<a[^>]+href="/odoo/action-30/(\d+)\?debug=1">([^<]+)</a>'
        else:
            view_pattern = r'<li>\s*<a[^>]+href="[^"]*id=(\d+)">([^<]+)</a>\s*</li>'
        matches = re.findall(view_pattern, disabled_views_section)
        disabled_views = env['ir.ui.view'].browse([int(view_id) for view_id, _ in matches])
        for view in disabled_views:
            try:
                view.write({'disabled_version': odoo_version})
            except Exception as e:
                # Missing record. The upgrade platform might have deleted the view already.
                continue
        return disabled_views
    
    def _extract_upgrade_version(html_string):
        version_pattern = r'<h2> Upgrade report: ([\d.]+) </h2>'
        version_match = re.search(version_pattern, html_string)
        if not version_match:
            version_pattern = r'<h2>\s*Congratulations, you have just upgraded to Odoo\s+([\d.]+)\s*</h2>'
            version_match = re.search(version_pattern, html_string)
        return version_match.group(1) if version_match else None
    
    channel_admin = env.ref("__upgrade__.channel_administrators", raise_if_not_found=False) or env.ref("mail.channel_admin")
    if channel_admin.message_ids:
        message_dates = channel_admin.message_ids.mapped(lambda m: m.create_date.date())
        max_date = max(message_dates, default=None)

        recent_messages = channel_admin.message_ids.filtered(lambda m: m.create_date.date() == max_date)

        for message in recent_messages:
            _process_disabled_views(str(message.body))
        for version in odoo_versions_to_write_scripts_for:
            env['upgrade.script'].create({'major_version': version})

def post_init_hook(env):
    _process_migration_report(env)
    
