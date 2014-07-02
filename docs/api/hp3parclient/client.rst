:mod:`client` -- HP3ParClient
===========================================

.. automodule:: hp3parclient.client
   :synopsis: HP 3PAR REST Web client

   .. autoclass:: hp3parclient.client.HP3ParClient(api_url)

      .. automethod:: getWsApiVersion
      .. automethod:: debug_rest
      .. automethod:: login
      .. automethod:: logout
      .. automethod:: setSSHOptions
      .. automethod:: getVolumes
      .. automethod:: getVolume
      .. automethod:: createVolume
      .. automethod:: deleteVolume
      .. automethod:: createSnapshot
      .. automethod:: getCPGs
      .. automethod:: getCPG
      .. automethod:: createCPG
      .. automethod:: deleteCPG
      .. automethod:: getVLUNs
      .. automethod:: getVLUN
      .. automethod:: createVLUN
      .. automethod:: deleteVLUN
      .. automethod:: createHost
      .. automethod:: modifyHost
      .. automethod:: getHosts
      .. automethod:: getHost
      .. automethod:: deleteHost
      .. automethod:: getHostVLUNs
      .. automethod:: getPorts
      .. automethod:: getFCPorts
      .. automethod:: getiSCSIPorts
      .. automethod:: getIPPorts
      .. automethod:: setVolumeMetaData
      .. automethod:: getVolumeMetaData
      .. automethod:: getAllVolumeMetaData
      .. automethod:: removeVolumeMetaData
      .. automethod:: findVolumeMetaData
