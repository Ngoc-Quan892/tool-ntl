# User Guide - Baccarat Predictor Pro

Hướng dẫn sử dụng ứng dụng Baccarat Predictor Pro cho người dùng cuối.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Interface Overview](#interface-overview)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Roadmaps](#roadmaps)
- [Statistics](#statistics)
- [Tips & Best Practices](#tips--best-practices)
- [Troubleshooting](#troubleshooting)

## 🚀 Getting Started

### First Launch

1. **Open the application** - Truy cập ứng dụng qua trình duyệt
2. **Create a new shoe** - Click "New Shoe" để bắt đầu
3. **Configure settings** (optional):
   - Number of decks (default: 8)
   - Reshuffle point (default: 20 cards remaining)

### Quick Start

1. Click **"New Shoe"** button
2. Start playing hands by clicking **"Banker"**, **"Player"**, or **"Tie"**
3. View predictions in the **Prediction Box**
4. Monitor statistics in the **Stats Panel**

## 🖥️ Interface Overview

### Main Components

#### 1. Control Panel
- **New Shoe**: Tạo shoe mới
- **Reset**: Reset current shoe
- **Undo**: Hoàn tác hand cuối cùng
- **Export**: Xuất dữ liệu

#### 2. Prediction Box
- Hiển thị prediction hiện tại (Banker/Player/Tie)
- Confidence score (0-100%)
- Edge calculation
- True count

#### 3. Roadmap Grid
- **Big Road**: Main roadmap
- **Small Road**: Derived roadmap
- **Cockroach Pig**: Pattern detection
- **Big Eye Boy**: Additional analysis

#### 4. Statistics Panel
- Win/loss counts
- Percentages
- Streaks
- Edge calculations

#### 5. History Table
- Complete hand history
- Filters và sorting
- Export capabilities

## 📖 Basic Usage

### Playing a Hand

1. **View Prediction**: Prediction box hiển thị recommendation
2. **Enter Result**: Click button tương ứng với kết quả thực tế
   - **B** (Banker)
   - **P** (Player)
   - **T** (Tie)
3. **Automatic Update**: Roadmaps và statistics tự động cập nhật

### Creating a New Shoe

1. Click **"New Shoe"** button
2. (Optional) Configure:
   - Number of decks
   - Reshuffle point
3. Click **"Create"**
4. Shoe mới được tạo và ready để play

### Resetting Current Shoe

1. Click **"Reset"** button
2. Confirm reset
3. Shoe được reset với cards mới, history được giữ lại

### Undoing Last Hand

1. Click **"Undo"** button
2. Hand cuối cùng được xóa
3. Roadmaps và statistics được cập nhật

## 🎯 Advanced Features

### Simulation Mode

1. Click **"Simulation"** button
2. Configure:
   - Number of shoes to simulate
   - Strategy settings
3. Click **"Run Simulation"**
4. View results và statistics

### Export Data

1. Click **"Export"** button
2. Choose format:
   - **CSV**: For spreadsheet analysis
   - **JSON**: For programmatic use
3. Download file

### Real-time Updates

- Predictions tự động cập nhật khi có hand mới
- WebSocket connection đảm bảo real-time sync
- No manual refresh needed

## 🗺️ Roadmaps

### Big Road

- Main roadmap visualization
- Shows Banker (red) và Player (blue) wins
- Ties không hiển thị trên Big Road

### Small Road

- Derived from Big Road
- Shows patterns và trends
- Useful for pattern recognition

### Cockroach Pig

- Advanced pattern detection
- Identifies clusters và streaks
- Helps với strategy decisions

### Big Eye Boy

- Additional analysis layer
- Complements other roadmaps
- Provides different perspective

## 📊 Statistics

### Win/Loss Counts

- **Banker Wins**: Số lần Banker thắng
- **Player Wins**: Số lần Player thắng
- **Ties**: Số lần Tie

### Percentages

- Win percentages cho mỗi outcome
- Updated in real-time

### Streaks

- Longest streaks
- Current streak
- Streak history

### Edge Calculation

- True count-based edge
- ML-based edge
- Combined recommendation

## 💡 Tips & Best Practices

### 1. Start Fresh

- Tạo shoe mới cho mỗi session
- Reset khi cards remaining thấp

### 2. Monitor Confidence

- High confidence (>70%): Strong recommendation
- Medium confidence (50-70%): Moderate recommendation
- Low confidence (<50%): Weak recommendation

### 3. Use Roadmaps

- Big Road: Overall trend
- Small Road: Short-term patterns
- Cockroach Pig: Cluster detection

### 4. Track Statistics

- Monitor win percentages
- Watch for streaks
- Calculate edge regularly

### 5. Export Data

- Export regularly để backup
- Analyze exported data với tools khác
- Keep historical records

## 🔧 Troubleshooting

### Prediction Not Updating

**Solution:**
1. Check WebSocket connection (should show "Connected")
2. Refresh page nếu cần
3. Check browser console cho errors

### Roadmaps Not Displaying

**Solution:**
1. Ensure có ít nhất 1 hand đã được played
2. Check browser console cho errors
3. Try resetting shoe

### Statistics Incorrect

**Solution:**
1. Verify hand history is correct
2. Check for duplicate entries
3. Try resetting và starting fresh

### Slow Performance

**Solution:**
1. Clear browser cache
2. Close other tabs
3. Check internet connection
4. Reduce number of hands in history

### Export Not Working

**Solution:**
1. Check browser allows downloads
2. Try different format (CSV vs JSON)
3. Check browser console cho errors

## 📞 Support

Nếu gặp vấn đề:

1. Check [Troubleshooting](#troubleshooting) section
2. Check browser console cho error messages
3. Contact support với:
   - Browser version
   - Error messages
   - Steps to reproduce

## 🔗 Related Documentation

- [Quick Start Guide](user-guide/quick-start.md)
- [Advanced Usage](user-guide/advanced-usage.md)
- [API Documentation](API_COMPLETE.md)

