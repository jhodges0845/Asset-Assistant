# SPDX-License-Identifier: GPL-3.0-or-later
from types import SimpleNamespace
import pytest
from blender_adapter import workflow_ui


class Layout:
    def __init__(self, events):
        self.events = events
        self.enabled = True
    def box(self): return Layout(self.events)
    def row(self): return Layout(self.events)
    def label(self, **kw): self.events.append(('label',kw.get('text')))
    def prop(self, *args, **kw): pass
    def operator(self, name, **kw): self.events.append((name,self.enabled))


@pytest.mark.parametrize('ready',[False,True])
def test_primary_actions_precede_validation_details(ready):
    events=[]
    settings=SimpleNamespace(target=object(),output_target='GODOT',
        validation_results=[SimpleNamespace(status='PASS' if ready else 'ERROR')],last_export='')
    context=SimpleNamespace(scene=SimpleNamespace(humanoid_settings=settings),region=SimpleNamespace(width=280))
    ui=SimpleNamespace(_export_issues=lambda c:settings.validation_results,
        is_ready=lambda rows:ready,
        _draw_validation_results=lambda *args:events.append(('details',None)))
    workflow_ui._draw_export(SimpleNamespace(layout=Layout(events)),context,ui,object())
    assert events.index(('humanoid.export_asset',ready)) < events.index(('details',None))
    assert events.index(('asset_assistant.save_editable_checkpoint',True)) < events.index(('details',None))
    if not ready:
        assert ('label','Run validation and resolve issues below.') in events


@pytest.mark.parametrize('changes,expected',[
    ({'export_name':True,'strength':False,'duration_seconds':False},'keeps keyframes'),
    ({'export_name':False,'strength':True,'duration_seconds':False},'regenerates keys'),
    ({'export_name':False,'strength':False,'duration_seconds':False},'no effective changes'),
])
def test_animation_summary_explains_curve_effect(changes,expected):
    from blender_adapter.animation_tuning_ui import _summary
    assert expected in _summary({'clip_id':'Idle','changes':changes})
