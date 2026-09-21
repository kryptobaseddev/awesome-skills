import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Settings } from 'lucide-react';

export function Toolbar({ onPress }: { onPress: () => void }) {
  return (
    <View style={styles.bar}>
      <Text style={styles.label} allowFontScaling={false}>Projects</Text>
      <Pressable onPress={onPress} style={{ width: 28, height: 28 }}>
        <Settings />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 56 },
  label: { fontSize: 9 },
});
