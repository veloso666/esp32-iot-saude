#!/usr/bin/env python3
"""Recadastra o End Device Radioenge no ChirpStack com o DevEUI real."""
import sys
import grpc
from chirpstack_api import api

SERVER = "localhost:8080"
DEV_EUI_REAL = "0012f80000003bb8"
DEV_EUI_OLD = "a15f964606e82507"
APP_KEY = "03ac61112108c8c446c139356326dcfc"
JOIN_EUI = "0000000000000000"
APP_NAME = "iot-saude"
PROFILE_NAME = "saude-au915-otaa"
DEV_NAME = "no-uti-01"

chan = grpc.insecure_channel(SERVER)
auth = None
for pwd in ("admin", "chirpstack", "admin123"):
    try:
        internal = api.InternalServiceStub(chan)
        r = internal.Login(api.LoginRequest(email="admin", password=pwd))
        auth = [("authorization", "Bearer %s" % r.jwt)]
        print("[OK] login admin (senha=%s)" % pwd)
        break
    except grpc.RpcError as e:
        print("[..] login falhou senha=%s: %s" % (pwd, e.details()))
if not auth:
    print("[ERRO] nao consegui logar como admin. Ajuste a senha no script.")
    sys.exit(1)

# tenant
ten = api.TenantServiceStub(chan)
tenant_id = ten.List(api.ListTenantsRequest(limit=100), metadata=auth).result[0].id
print("[OK] tenant:", tenant_id)

# application
app_stub = api.ApplicationServiceStub(chan)
apps = app_stub.List(api.ListApplicationsRequest(limit=100, tenant_id=tenant_id), metadata=auth).result
app_id = next((a.id for a in apps if a.name == APP_NAME), None)
print("[OK] application %s:" % APP_NAME, app_id)

# device profile
dp_stub = api.DeviceProfileServiceStub(chan)
dps = dp_stub.List(api.ListDeviceProfilesRequest(limit=100, tenant_id=tenant_id), metadata=auth).result
dp_id = next((d.id for d in dps if d.name == PROFILE_NAME), None)
print("[OK] device_profile %s:" % PROFILE_NAME, dp_id)

if not app_id or not dp_id:
    print("[ERRO] application ou device_profile nao encontrados.")
    sys.exit(1)

dev_stub = api.DeviceServiceStub(chan)

# apaga device antigo (DevEUI inventado), se existir
try:
    dev_stub.Delete(api.DeleteDeviceRequest(dev_eui=DEV_EUI_OLD), metadata=auth)
    print("[OK] device antigo removido:", DEV_EUI_OLD)
except grpc.RpcError as e:
    print("[..] device antigo nao removido (%s)" % e.details())

# cria device com DevEUI real
d = api.Device(
    dev_eui=DEV_EUI_REAL,
    name=DEV_NAME,
    description="Radioenge RD49C - DevEUI real do modulo",
    application_id=app_id,
    device_profile_id=dp_id,
    is_disabled=False,
    join_eui=JOIN_EUI,
)
try:
    dev_stub.Create(api.CreateDeviceRequest(device=d), metadata=auth)
    print("[OK] device criado:", DEV_EUI_REAL)
except grpc.RpcError as e:
    print("[..] create device (%s) - tentando atualizar" % e.details())
    dev_stub.Update(api.UpdateDeviceRequest(device=d), metadata=auth)
    print("[OK] device atualizado:", DEV_EUI_REAL)

# grava AppKey (LoRaWAN 1.0.x -> nwk_key)
keys = api.DeviceKeys(dev_eui=DEV_EUI_REAL, nwk_key=APP_KEY, app_key=APP_KEY)
try:
    dev_stub.CreateKeys(api.CreateDeviceKeysRequest(device_keys=keys), metadata=auth)
    print("[OK] chaves criadas (AppKey=%s)" % APP_KEY)
except grpc.RpcError as e:
    dev_stub.UpdateKeys(api.UpdateDeviceKeysRequest(device_keys=keys), metadata=auth)
    print("[OK] chaves atualizadas (AppKey=%s)" % APP_KEY)

print("\n=== PRONTO ===")
print("DevEUI :", DEV_EUI_REAL)
print("JoinEUI:", JOIN_EUI)
print("AppKey :", APP_KEY)
