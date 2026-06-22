fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&[
                "get_storage_health",
                "create_task",
                "list_tasks",
                "move_task",
                "reorder_task",
                "update_task_title",
            ]),
        ),
    )
    .expect("failed to run tauri build script");
}
