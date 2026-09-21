package com.example.app

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.widget.Toast
import android.widget.Switch

@Composable
fun HomeScreen(onOpen: () -> Unit) {
    val alpha by animateFloatAsState(targetValue = 1f)

    Scaffold(
        bottomBar = { NavigationBar { } },
        floatingActionButton = {
            FloatingActionButton(onClick = onOpen) { }
            FloatingActionButton(onClick = onOpen) { }
        }
    ) {
        Row {
            Text(
                text = "Projects",
                fontSize = 22.sp,
                color = Color(0xFF1A1A1A),
                fontFamily = FontFamily(Font(R.font.satoshi))
            )
            Text(text = "subtitle", fontSize = 13.dp)
            IconButton(onClick = onOpen, modifier = Modifier.size(32.dp)) { }
        }
        Surface(modifier = Modifier.shadow(elevation = 8.dp)) { }
    }

    BackHandler(enabled = true) { }

    Toast.makeText(context, "Saved", Toast.LENGTH_SHORT).show()
}

fun setup() {
    enableEdgeToEdge()
}

val AppColors = lightColorScheme(primary = Color(0xFF6750A4))
