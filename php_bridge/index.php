<?php
// Future SyMoNeuRaL PHP control-plane entry.
// For now, proxy to the Python/FastAPI reference app or reimplement /api/v1 routes here.
header('Content-Type: application/json');
echo json_encode([
  'service' => 'SyMoNeuRaL PHP bridge placeholder',
  'active_control_plane' => 'Python/FastAPI',
  'next_step' => 'Reimplement stable /api/v1 schema in PHP without changing engine binaries.'
], JSON_PRETTY_PRINT);
