# 🏕️ CampBot Future Roadmap

## 🐛 **Bug Fixes & Core Issues**
- [x] ~~Fix search names with multiple words parsing issues. currently, when the user given name for a search has two+ words, it does not parse correctly, and confuses the 2nd word with the start of the date.~~ **COMPLETED ✅**
- [ ] Improve date formatting for better user readability  
- [ ] Handle recreation.gov API rate limits gracefully
- [ ] Fix edge cases with date range validation
- [ ] Improve error messages for invalid park IDs

## 🎨 **User Experience Improvements**
- [ ] Add date picker/calendar interface for easier date selection
- [ ] Replace command-line interface with inline keyboard UI in Telegram
- [ ] Implement user onboarding flow with interactive tutorial
- [ ] Create user settings and preferences system
- [ ] Add support for campsite type preferences (RV, tent, etc.)

## 🔔 **Notification Management**
- [ ] Implement auto-pause notifications after booking window closes
- [ ] Add pause/resume all notifications function
- [ ] Add configurable search frequency/priority levels
- [ ] Create smart notification scheduling (avoid night spam)
- [ ] Add "snooze" functionality for temporary notification pause

## 📚 **Documentation & Onboarding**
- [ ] Create comprehensive user guide for getting started with campbot
- [ ] Revise language and tone to match personal communication style

## 🎯 **Branding & Polish**
- [ ] Design and add logo/branding to bot and notifications
- [ ] Create consistent visual identity
- [ ] Add custom bot profile picture and description

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

## ⚡ **Performance & Scaling**
- [ ] Conduct UAT with multiple concurrent searches
- [ ] Perform stress testing and assess cost implications  
- [ ] Add search result caching to reduce API calls. Or maybe if multiple users are checking the same campground for same dates, we should only hit the api once for that date
- [ ] Optimize Lambda cold start times

## 💰 **Business Features**
- [ ] Research and implement monetization strategy
- [ ] Add usage analytics for pricing tiers
- [ ] Create premium features (faster checks, priority support)

## 🗺️ **Enhanced Features**
- [ ] Add direct booking URLs to availability notifications
- [ ] Create database of known park IDs with names/locations
- [ ] Add integration with other camping platforms beyond recreation.gov
- [ ] Add support for recreation.gov wilderness permits (priority)

---

## 🏆 **MVP Completed ✅**
- ✅ Multi-user Telegram bot interface
- ✅ Scheduled monitoring via EventBridge  
- ✅ S3-based user configuration storage
- ✅ Manual check functionality
- ✅ Clean, scalable architecture
- ✅ Robust error handling and logging
