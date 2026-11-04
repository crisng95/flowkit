const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('spikeApi', {
  getPublicSurface: () => ipcRenderer.invoke('spike:get-public-surface'),
  tryRequestSecret: () => ipcRenderer.invoke('spike:renderer-request-secret')
});
