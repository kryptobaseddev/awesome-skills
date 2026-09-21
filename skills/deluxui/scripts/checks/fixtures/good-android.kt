package com.example.app

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.windowsizeclass.WindowWidthSizeClass
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun HomeScreen(widthClass: WindowWidthSizeClass, onOpen: () -> Unit) {
    val snackbarHostState = remember { SnackbarHostState() }
    val scale = Settings.Global.getFloat(
        resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f
    )

    Scaffold(
        modifier = Modifier.safeDrawingPadding(),
        topBar = { TopAppBar(title = { Text("Projects") }) },
        bottomBar = {
            if (widthClass == WindowWidthSizeClass.Compact) NavigationBar { }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            FloatingActionButton(onClick = onOpen) { }
        }
    ) {
        Row {
            Text(
                text = "Projects",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            IconButton(
                onClick = onOpen,
                modifier = Modifier.minimumInteractiveComponentSize()
            ) { }
        }
        Surface(tonalElevation = 3.dp) { }
    }

    BackHandler(enabled = true) { onOpen() }
}

@Composable
fun AppTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val scheme = when {
        supportsDynamic() && dark -> dynamicDarkColorScheme(LocalContext.current)
        supportsDynamic() -> dynamicLightColorScheme(LocalContext.current)
        dark -> darkColorScheme()
        else -> lightColorScheme()
    }
    MaterialTheme(colorScheme = scheme, content = content)
}

@Composable
fun NavHostSide(widthClass: WindowWidthSizeClass) {
    if (widthClass != WindowWidthSizeClass.Compact) NavigationRail { }
}
