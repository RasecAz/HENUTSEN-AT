<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
  <h1>Módulo Henutsen - RFID ArisTextil</h1>

  <h2>Descripción</h2>

  <p>
    Módulo para el proyecto Odoo Aristextil que extiende la funcionalidad del modelo `stock`,`sales`, `purchases`, `users` y `contacts` para optimizar los procesos de Aristextil.
  </p>

  <h2>Funcionalidades</h2>

  <ul>
    <li>Webservice de Picking, packing y ajuste de inventarios con Henutsen.</li>
    <li>Generación de JSON para el sistema CG1.</li>
    <li>Flujo de aprobación en módulo de ventas.</li>
    <li>Campos adicionales en módulo de Compras.</li>
    <li>Campos adicionales en módulo de Inventarios.</li>
    <li>Campos adicionales en módulo de Contactos y Usuarios.</li>
    <li>Validaciones extra a los procesos de inventarios.</li>
  </ul>

  <h2>Dependencias</h2>

  <ul>
    <li>Odoo 17</li>
    <li>Módulo Inventarios. Modelo stock</li>
    <li>Módulo Ventas. Modelo sales</li>
    <li>Módulo Compras. Modelo purchases</li>
    <li>Módulo Contactos. Modelo contacts</li>
  </ul>

  <h2>Instalación</h2>

  <ol>
    <li>Asegurarse de que toda la configuración previa de Odoo se haya completado.</li>
    <li>Actualizar base de datos</li>
    <li>Instalar el módulo en la sección de aplicaciones (asegurarse que los módulos dependencias estén instalados).</li>
    <li>Activar el modo desarrollador como Administrador</li>
    <li>Configurar parámetros de webservices: Ingresar a Inventarios -- Configuración -- Ajustes Henutsen. Registrar todos los campos, activar el Bearer token y seleccionar la opción `Guardar`</li>
  </ol>

  <h2>Desarrollador</h2>

  <p>
    * Wilson Contreras <br/>
    * Desarrollador Python Odoo
  </p>
  
