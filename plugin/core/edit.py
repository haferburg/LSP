import os
import sublime
import sublime_plugin

try:
    from typing import List, Dict, Optional
    assert List and Dict and Optional
except ImportError:
    pass

from .url import uri_to_filename
from .protocol import Range
from .logging import debug
from .workspace import get_project_path
from .views import range_to_region


class LspApplyWorkspaceEditCommand(sublime_plugin.WindowCommand):
    def run(self, changes=None, document_changes=None):
        documents_changed = 0
        if changes:
            for uri, file_changes in changes.items():
                path = uri_to_filename(uri)
                self.open_and_apply_edits(path, file_changes)
                documents_changed += 1
        elif document_changes:
            for document_change in document_changes:
                uri = document_change.get('textDocument').get('uri')
                path = uri_to_filename(uri)
                self.open_and_apply_edits(path, document_change.get('edits'))
                documents_changed += 1

        if documents_changed > 0:
            message = 'Applied changes to {} documents'.format(documents_changed)
            self.window.status_message(message)
        else:
            self.window.status_message('No changes to apply to workspace')

    def open_and_apply_edits(self, path, file_changes):
        view = self.window.open_file(path)
        if view:
            if view.is_loading():
                # TODO: wait for event instead.
                sublime.set_timeout_async(
                    lambda: view.run_command('lsp_apply_document_edit', {'changes': file_changes}),
                    500
                )
            else:
                view.run_command('lsp_apply_document_edit',
                                 {'changes': file_changes,
                                  'show_status': False})
        else:
            debug('view not found to apply', path, file_changes)


class LspApplyDocumentEditCommand(sublime_plugin.TextCommand):
    def run(self, edit, changes: 'Optional[List[dict]]' = None, show_status=True):
        # We want to apply the changes in reverse, so that we don't invalidate the range
        # of any change that we haven't applied yet.
        changes = self.changes_sorted_in_reverse(changes) if changes else []
        for change in changes:
            self.apply_change(self.create_region(change), change.get('newText'), edit)

        if show_status:
            window = self.view.window()
            if window:
                base_dir = get_project_path(window)
                file_path = self.view.file_name()
                relative_file_path = os.path.relpath(file_path, base_dir) if base_dir else file_path
                message = 'Applied {} change(s) to {}'.format(len(changes), relative_file_path)
                window.status_message(message)

    def changes_sorted_in_reverse(self, changes: 'List[dict]') -> 'List[Dict]':
        # Changes look like this:
        # [
        #   {
        #       'newText': str,
        #       'range': {
        #            'start': {'line': int, 'character': int},
        #            'end': {'line': int, 'character': int}
        #       }
        #   }
        # ]

        def get_start_position(ic):
            index = ic[0]
            change = ic[1]
            start = change.get('range').get('start')
            line = start.get('line')
            character = start.get('character')
            return (line, character, index)

        # The spec reads:
        # > However, it is possible that multiple edits have the same start position: multiple
        # > inserts, or any number of inserts followed by a single remove or replace edit. If
        # > multiple inserts have the same position, the order in the array defines the order in
        # > which the inserted strings appear in the resulting text.
        # So we sort by start position. But if multiple text edits start at the same position,
        # we use the index in the array as the key.
        indexed_changes = [(i, c) for i, c in enumerate(changes)]
        indexed_changes = sorted(indexed_changes, key=get_start_position, reverse=True)
        return [ic[1] for ic in indexed_changes]

    def create_region(self, change):
        return range_to_region(Range.from_lsp(change['range']), self.view)

    def apply_change(self, region, newText, edit):
        if region.empty():
            self.view.insert(edit, region.a, newText)
        else:
            if len(newText) > 0:
                self.view.replace(edit, region, newText)
            else:
                self.view.erase(edit, region)
