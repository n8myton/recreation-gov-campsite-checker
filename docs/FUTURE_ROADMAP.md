# 🏕️ CampBot Future Roadmap

## 🎉 **Recently Completed**
- [x] ~~Fix search names with multiple words parsing issues~~ **COMPLETED ✅**
- [x] ~~Handle recreation.gov API rate limits gracefully~~ **COMPLETED ✅** - Smart error filtering for 429s, timeouts, and transient errors
- [x] ~~Add direct booking URLs to availability notifications~~ **COMPLETED ✅** - Links now included in all notifications
- [x] ~~Add custom bot profile picture and description~~ **COMPLETED ✅**
- [x] ~~Remove legacy single-user mode and Pushover support~~ **COMPLETED ✅** - Streamlined to multi-user Telegram only
- [x] ~~Simplify EventBridge payload requirements~~ **COMPLETED ✅** - Now uses environment variables only

## 🐛 **Bug Fixes & Core Issues**
- [ ] Improve date formatting for better user readability  
- [ ] Fix edge cases with date range validation (if needed)
- [ ] Improve error messages for invalid park IDs (if needed)

## 🎨 **User Experience Improvements**
- [ ] Add date picker/calendar interface for easier date selection
- [ ] Replace command-line interface with inline keyboard UI in Telegram
- [ ] Add support for campsite type preferences (RV, tent, etc.) filtering
- [ ] Add `/lookup` command - search park names and get park IDs from recreation.gov

## 🔔 **Notification Management**
- [ ] Implement auto-pause notifications after booking window closes
- [ ] Add pause/resume all notifications function
- [ ] Add notification preferences (time windows, max per day, etc.)

## 🎯 **Branding & Polish**
- [ ] Design and add logo/branding to bot and notifications
- [ ] Revise language and tone to match personal communication style

## 🔧 **System Reliability**
- [ ] Implement bug report function for users
- [ ] Add search analytics and success rate tracking
- [ ] Create admin dashboard for system monitoring
- [ ] Add comprehensive error tracking and alerts
  - [ ] **Set up CloudWatch Alarms + SNS email notifications** (Option 1 - simplest, no code changes)
    - Configure CloudWatch Alarms for Lambda errors/throttles
    - Create SNS topic with email subscription for admin alerts
    - Set up alarms for both `campbot` and `telegram_bot` Lambda functions
    - Optional: CloudWatch Log Insights saved queries for common error patterns

## 🗺️ **Enhanced Features**
- [ ] Add support for recreation.gov wilderness permits (high priority)
- [ ] Support for tour/activity reservations
- [ ] Multi-park search optimization (batch API calls)

---

## 🏆 **MVP Completed ✅**
- ✅ Multi-user Telegram bot interface
- ✅ Scheduled monitoring via EventBridge  
- ✅ S3-based user configuration storage
- ✅ Manual check functionality
- ✅ Clean, scalable architecture
- ✅ Robust error handling and logging
