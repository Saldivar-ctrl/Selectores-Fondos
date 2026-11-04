"""Pruebas de los backends SIN sistemas reales: procesos y D-Bus simulados.

Lo que NO demuestran: que Wallpaper Engine, Lively o waywallen reaccionen
bien en una máquina real. Eso está en docs/PRUEBAS.md como pendiente.
"""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from _comun import CasoAislado

from selectores_fondos import platforms
from selectores_fondos.core.gestor_fondos import Fondo
from selectores_fondos.platforms.base import ErrorBackend
from selectores_fondos.platforms.linux import waywallen as ww


def varint(n):
    salida = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        salida.append(b | (0x80 if n else 0))
        if not n:
            return bytes(salida)


def campo(num, wire, valor):
    clave = varint((num << 3) | wire)
    if wire == 0:
        return clave + varint(valor)
    if isinstance(valor, str):
        valor = valor.encode()
    return clave + varint(len(valor)) + valor


def entrada(ident, nombre, tipo, recurso, size):
    return campo(1, 2, campo(1, 2, ident) + campo(2, 2, nombre)
                 + campo(3, 2, tipo) + campo(4, 2, recurso) + campo(7, 0, size))


class PruebasWaywallen(CasoAislado):

    def frame(self, entradas, ident=1):
        listado = b"".join(entradas)
        respuesta = campo(1, 0, ident) + campo(19, 2, listado)
        return campo(1, 2, respuesta)

    def test_parsea_el_catalogo(self):
        f = self.frame([entrada("a1", "Playa", "video", "/x/playa.mp4", 10)])
        self.assertEqual(ww.parsear_respuesta_catalogo(f), [{
            "id": "a1", "name": "Playa", "type": "video",
            "resource": "/x/playa.mp4", "size": 10}])

    def test_ignora_respuestas_de_otra_peticion(self):
        f = self.frame([entrada("a1", "P", "v", "/x", 1)], ident=2)
        self.assertIsNone(ww.parsear_respuesta_catalogo(f))

    def test_error_del_daemon(self):
        f = campo(1, 2, campo(1, 0, 1) + campo(3, 2, "sin biblioteca"))
        with self.assertRaises(RuntimeError):
            ww.parsear_respuesta_catalogo(f)

    def test_protobuf_truncado_da_error(self):
        with self.assertRaises(ValueError):
            list(ww._ww_fields(b"\x0a\x10abc"))  # promete 16 bytes

    def test_busca_archivo_suelto_por_nombre_y_tamano(self):
        v = self.dir / "mar.mp4"
        v.write_bytes(b"x" * 7)
        cat = [
            {"id": "1", "name": "", "type": "", "resource": "/otro/mar.mp4", "size": 3},
            {"id": "2", "name": "", "type": "", "resource": "/ruta/mar.mp4", "size": 7},
        ]
        self.assertEqual(ww.find_waywallen_id(str(v), cat), "2")

    def test_archivo_no_registrado(self):
        v = self.dir / "solo.mp4"
        v.write_bytes(b"x")
        with self.assertRaises(ValueError):
            ww.find_waywallen_id(str(v), [])

    def test_proyecto_por_carpeta_titulo_y_enlace_simbolico(self):
        real = self.dir / "real/431960/999"
        real.mkdir(parents=True)
        (real / "scene.pkg").write_bytes(b"x")
        (real / "project.json").write_text('{"title": "Neón"}', encoding="utf-8")
        enlace = self.dir / "enlace"
        enlace.symlink_to(self.dir / "real")
        ruta_via_enlace = enlace / "431960/999/scene.pkg"

        # 1) catálogo con la ruta real, local con enlace -> realpath
        cat = [{"id": "w1", "name": "x", "type": "", "size": 0,
                "resource": str(real / "scene.pkg")}]
        self.assertEqual(ww.find_waywallen_id(str(ruta_via_enlace), cat), "w1")

        # 2) por número de carpeta de Steam
        cat = [{"id": "w2", "name": "x", "type": "", "size": 0,
                "resource": "/otra/431960/999/scene.json"}]
        self.assertEqual(ww.find_waywallen_id(str(real / "scene.pkg"), cat), "w2")

        # 3) por título
        cat = [{"id": "w3", "name": "neón", "type": "", "size": 0,
                "resource": "/zzz/a.json"}]
        self.assertEqual(ww.find_waywallen_id(str(real / "scene.pkg"), cat), "w3")

    def test_aplicar_llama_a_busctl_sin_shell_y_con_el_id(self):
        v = self.dir / "mar.mp4"
        v.write_bytes(b"x")
        b = ww.WaywallenBackend(self.config)
        capturado = {}

        def falso_run(cmd, **kw):
            capturado["cmd"] = cmd
            capturado["kw"] = kw
            return subprocess.CompletedProcess(cmd, 0, stdout="b true", stderr="")

        with mock.patch.object(ww, "waywallen_catalog", return_value=[
                {"id": "ID7", "name": "", "type": "", "resource": str(v), "size": 1}]), \
             mock.patch.object(ww.subprocess, "run", falso_run):
            mensaje = b.aplicar(Fondo(path=str(v)))

        self.assertEqual(capturado["cmd"][-3:], ["ApplyById", "s", "ID7"])
        self.assertNotIn("shell", capturado["kw"])
        self.assertIn("mar.mp4", mensaje)

    def test_aplicar_con_timeout_no_es_error(self):
        v = self.dir / "pesado.mp4"
        v.write_bytes(b"x")
        b = ww.WaywallenBackend(self.config)

        def lento(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 15)

        with mock.patch.object(ww, "waywallen_catalog", return_value=[
                {"id": "1", "name": "", "type": "", "resource": str(v), "size": 1}]), \
             mock.patch.object(ww.subprocess, "run", lento):
            self.assertIn("se está cargando", b.aplicar(Fondo(path=str(v))))

    def test_aplicar_archivo_inexistente(self):
        with self.assertRaises(ErrorBackend):
            ww.WaywallenBackend(self.config).aplicar(Fondo(path="/no/existe.mp4"))

    def test_filtrar_registrados(self):
        a = self.dir / "a.mp4"
        b = self.dir / "b.mp4"
        a.write_bytes(b"1")
        b.write_bytes(b"1")
        backend = ww.WaywallenBackend(self.config)
        cat = [{"id": "1", "name": "", "type": "", "resource": str(a), "size": 1}]
        fondos = [Fondo(path=str(a)), Fondo(path=str(b))]

        with mock.patch.object(ww, "waywallen_catalog", return_value=cat):
            self.assertEqual([f.path for f in backend.filtrar_registrados(fondos)],
                             [str(a)])

            self.config.ocultar_no_registrados = False
            self.assertEqual(len(backend.filtrar_registrados(fondos)), 2)

    def test_sin_waywallen_se_muestran_todos(self):
        fondos = [Fondo(path="/x")]
        with mock.patch.object(ww, "waywallen_catalog",
                               side_effect=ErrorBackend("no hay daemon")):
            self.assertEqual(
                ww.WaywallenBackend(self.config).filtrar_registrados(fondos), fondos)


class PruebasWindows(CasoAislado):
    """Se ejecutan en cualquier sistema: no usan nada propio de Windows."""

    def setUp(self):
        super().setUp()
        from selectores_fondos.platforms.windows import lively_wallpaper as lv
        from selectores_fondos.platforms.windows import wallpaper_engine as we
        self.we, self.lv = we, lv

        self.exe_we = self.dir / "Steam con espacio" / "wallpaper64.exe"
        self.exe_lv = self.dir / "Lively Wallpaper" / "Lively.exe"
        for p in (self.exe_we, self.exe_lv):
            p.parent.mkdir(parents=True)
            p.write_bytes(b"MZ")

    def test_comando_de_wallpaper_engine_segun_la_documentacion(self):
        self.config.ruta_wallpaper_engine = str(self.exe_we)
        self.config.monitor = "1"
        b = self.we.WallpaperEngineBackend(self.config)
        cmd = b.construir_comando(self.exe_we, "C:\\Mis fondos\\project.json")
        self.assertEqual(cmd, [str(self.exe_we), "-control", "openWallpaper",
                               "-file", "C:\\Mis fondos\\project.json",
                               "-monitor", "1"])

    def test_wallpaper_engine_usa_project_json_y_no_usa_shell(self):
        self.config.ruta_wallpaper_engine = str(self.exe_we)
        d = self.dir / "w"
        d.mkdir()
        (d / "project.json").write_text("{}")
        (d / "a.mp4").write_bytes(b"x")
        visto = {}

        def falso(cmd, **kw):
            visto["cmd"], visto["kw"] = cmd, kw
            return subprocess.CompletedProcess(cmd, 0, "", "")

        b = self.we.WallpaperEngineBackend(self.config)
        with mock.patch.object(self.we, "proceso_en_ejecucion", return_value=True), \
             mock.patch.object(self.we.subprocess, "run", falso):
            b.aplicar(Fondo(path=str(d / "a.mp4"), proyecto=str(d / "project.json")))

        self.assertEqual(visto["cmd"][4], str(d / "project.json"))
        self.assertNotIn("shell", visto["kw"])

    def test_wallpaper_engine_no_instalado_da_mensaje_claro(self):
        self.config.ruta_wallpaper_engine = str(self.dir / "nada.exe")
        b = self.we.WallpaperEngineBackend(self.config)
        self.assertFalse(b.comprobar().ok)
        with self.assertRaises(ErrorBackend) as e:
            b.aplicar(Fondo(path="x"))
        self.assertIn("No se encontró Wallpaper Engine", str(e.exception))

    def test_wallpaper_engine_error_de_proceso(self):
        self.config.ruta_wallpaper_engine = str(self.exe_we)
        v = self.dir / "v.mp4"
        v.write_bytes(b"x")
        b = self.we.WallpaperEngineBackend(self.config)
        with mock.patch.object(self.we, "proceso_en_ejecucion", return_value=True), \
             mock.patch.object(self.we.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 1, "", "falló")):
            with self.assertRaises(ErrorBackend):
                b.aplicar(Fondo(path=str(v)))

    def test_comando_de_lively_segun_la_documentacion(self):
        self.config.ruta_lively = str(self.exe_lv)
        b = self.lv.LivelyBackend(self.config)
        self.assertEqual(
            b.construir_comando(self.exe_lv, "D:\\Vídeos\\mar.mp4"),
            [str(self.exe_lv), "setwp", "--file", "D:\\Vídeos\\mar.mp4"])

        self.config.monitor = "0"
        self.assertEqual(b.construir_comando(self.exe_lv, "x")[-2:], ["--monitor", "0"])

    def test_lively_no_instalado(self):
        self.config.ruta_lively = str(self.dir / "no.exe")
        b = self.lv.LivelyBackend(self.config)
        self.assertFalse(b.comprobar().ok)
        with self.assertRaises(ErrorBackend):
            b.aplicar(Fondo(path="x"))

    def test_lively_no_entiende_wallpaper_engine(self):
        self.assertFalse(self.lv.LivelyBackend(self.config).usa_wallpaper_engine)

    def test_ruta_que_no_es_exe_se_rechaza(self):
        falso = self.dir / "script.bat"
        falso.write_text("echo")
        self.config.ruta_lively = str(falso)
        self.assertIsNone(self.lv.LivelyBackend(self.config).ejecutable())


class PruebasSeleccion(CasoAislado):

    def test_backend_no_valido_para_el_sistema(self):
        self.config.backend = "lively" if platforms.sistema() == "linux" else "waywallen"
        with self.assertRaises(ErrorBackend):
            platforms.crear_backend(self.config)

    def test_auto_en_linux_es_waywallen(self):
        if platforms.sistema() != "linux":
            self.skipTest("solo Linux")
        self.assertEqual(platforms.crear_backend(self.config).id, "waywallen")

    def test_sistema_no_soportado(self):
        with mock.patch.object(platforms, "sistema", return_value="macos"):
            with self.assertRaises(ErrorBackend):
                platforms.crear_backend(self.config)


if __name__ == "__main__":
    unittest.main()
