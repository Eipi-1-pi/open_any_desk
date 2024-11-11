import sys
import ctypes
import win32serviceutil
import win32service
import win32event
import servicemanager
import psutil
import time
import subprocess
import os

class MonitorApplicationsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MonitorApplicationsService"
    _svc_display_name_ = "Monitor Applications Service"
    _svc_description_ = "A service that ensures LogMeIn and AnyDesk are running, and prevents shutdown if critical."
    # Add this line to set automatic start
    _svc_start_type_ = win32service.SERVICE_AUTO_START

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def get_process_count(self, process_name):
        count = 0
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'].lower() == process_name.lower():
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return count

    def is_app_running(self, process_name):
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'].lower() == process_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def restart_app(self, app_path, process_name):
        if not self.is_app_running(process_name):
            try:
                if process_name.lower() == "anydesk.exe":
                    subprocess.Popen([app_path, "--start-service"], 
                                  shell=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen(app_path, 
                                  shell=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(2)
            except Exception:
                pass

    def prevent_shutdown(self):
        try:
            ctypes.windll.advapi32.AbortSystemShutdownW(None)
        except Exception:
            pass

    def main(self):
        monitored_apps = {
            "AnyDesk.exe": r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
            "LogMeIn.exe": r"C:\Program Files (x86)\LogMeIn\x86\LogMeIn.exe"
        }

        while self.running:
            try:
                for process_name, app_path in monitored_apps.items():
                    if os.path.exists(app_path):
                        self.restart_app(app_path, process_name)
                rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
            except Exception:
                time.sleep(5)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MonitorApplicationsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MonitorApplicationsService)