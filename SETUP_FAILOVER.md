
# X Account Failover Setup

## Step 1: Create Second X Account
1. Create a new X (Twitter) account
2. Apply for Developer API access at https://developer.twitter.com
3. Create a new app and get API credentials

## Step 2: Add Secrets in Replit
Add these new secrets in the Secrets pane:

**Failover Account (Account 2):**
- `X_CONSUMER_KEY_2` - Your second account's consumer key
- `X_CONSUMER_SECRET_2` - Your second account's consumer secret  
- `X_ACCESS_TOKEN_2` - Your second account's access token
- `X_ACCESS_TOKEN_SECRET_2` - Your second account's access token secret

**Keep Existing (Account 1):**
- `X_CONSUMER_KEY` - Your primary account's consumer key
- `X_CONSUMER_SECRET` - Your primary account's consumer secret
- `X_ACCESS_TOKEN` - Your primary account's access token  
- `X_ACCESS_TOKEN_SECRET` - Your primary account's access token secret

## Step 3: Test Both Accounts
Run this to verify both accounts work:
```bash
python test_x_failover.py
```

## How It Works
1. **Primary First**: Always tries Account 1 first
2. **Auto Switch**: When Account 1 hits rate limits, switches to Account 2
3. **Seamless**: Posts continue without interruption
4. **Double Capacity**: 3,000 tweets/month total (1,500 each account)

## Rate Limit Benefits
- **Monthly**: 1,500 + 1,500 = 3,000 tweets/month
- **Daily**: ~50 + ~50 = ~100 tweets/day  
- **Hourly**: More flexibility during peak posting
