"""Safety boundary for native application actions; never act on another client."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('application_bridge',Path(__file__).resolve().parents[1]/'districts.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

class ApplicationTests(unittest.TestCase):
 def client(self,**changes):return dict({'pid':42,'class':'org.quickshell','title':'Districts','address':'0x123','mapped':True,'floating':True,'fullscreen':0,'size':[1200,800]},**changes)
 def test_unavailable_lua_never_dispatches(self):
  with patch.object(bridge,'lua_supported',return_value=False),patch.object(bridge,'command')as command:
   with self.assertRaisesRegex(RuntimeError,'Lua'):bridge.application_frame('toggle')
   command.assert_not_called()
 def test_other_pid_title_class_unmapped_never_dispatch(self):
  for client in [self.client(pid=43),self.client(title='Other'),self.client(class_='Other'),self.client(mapped=False)]:
   if 'class_'in client:client['class']=client.pop('class_')
   with patch.object(bridge,'os')as os,patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'query',return_value=[client]),patch.object(bridge,'command')as command:
    os.getppid.return_value=42
    with self.assertRaises(ValueError):bridge.application_frame('toggle')
    command.assert_not_called()
 def test_duplicate_or_malicious_address_never_dispatch(self):
  for clients in [[self.client(),self.client(address='0x456')],[self.client(address='0x123"}')]]:
   with patch.object(bridge.os,'getppid',return_value=42),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'query',return_value=clients),patch.object(bridge,'command')as command:
    with self.assertRaises(ValueError):bridge.application_frame('toggle')
    command.assert_not_called()
 def test_target_is_revalidated_before_dispatch(self):
  with patch.object(bridge.os,'getppid',return_value=42),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'query',side_effect=[[self.client()],[self.client(address='0x456')]]),patch.object(bridge,'command')as command:
   with self.assertRaisesRegex(ValueError,'changed'):bridge.application_frame('toggle')
   command.assert_not_called()
 def test_toggle_addresses_only_parent_window(self):
  with patch.object(bridge.os,'getppid',return_value=42),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'query',side_effect=[[self.client()],[self.client()],[self.client(fullscreen=1)]]),patch.object(bridge,'command',return_value='ok')as command:
   self.assertTrue(bridge.application_frame('toggle')['maximized'])
   command.assert_called_once_with(['dispatch','hl.dsp.window.fullscreen_state({ internal=1, client=1, action="set", window="address:0x123" })'])

if __name__=='__main__':unittest.main()
