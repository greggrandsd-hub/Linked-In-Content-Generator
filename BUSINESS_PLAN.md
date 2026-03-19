# LinkedIn Content Engine — Business Plan

## The Offering: Done-For-You LinkedIn Presence

Two services bundled together:

### 1. LinkedIn Profile Tune-Up (One-Time)
- Greg already does LinkedIn trainings — this is his existing expertise
- Audit and rewrite: headline, about section, experience, featured section
- Professional headshot guidance
- SEO optimization for their target audience
- Turn on creator mode / follow button
- Pricing: Part of the setup fee

### 2. LinkedIn Content Engine (Monthly Recurring)
- Custom voice-trained AI generates posts in the client's authentic voice
- Posts based on their own "20 Truths" theme bank (built during onboarding)
- Client receives email with 3 options, picks their favorite
- Greg reviews for quality, posts to their LinkedIn
- Images generated for each post (no text on images)
- No hashtags — clean staccato style


## Pricing Tiers

### Setup Fee: $1,500 (one-time)
- 60-min voice interview to capture their tone, stories, opinions
- Build their custom 20-theme bank
- Write 3 example posts as "voice samples" for AI training
- Set up all APIs (Dropbox, Gemini, Gmail, LinkedIn)
- LinkedIn profile tune-up (audit + rewrite)
- Test run with first week of posts for approval

### Starter: $500/month
- 2 posts per week (8/month)
- Greg generates and emails options
- Client self-approves and self-posts (or copy/paste from email)
- Monthly theme refresh

### Growth: $1,000/month
- 3 posts per week (12/month)
- Greg generates, client approves, Greg posts for them
- Monthly voice refresh call (15 min)
- Basic engagement tracking

### Premium: $2,000/month
- 5 posts per week (20/month)
- Full management — generate, review, post, done
- Image creation for every post
- Monthly strategy call (30 min)
- Engagement strategy (comment recommendations)
- Quarterly theme bank refresh


## Revenue Projections

| Clients | Tier    | Monthly  | Annual   |
|---------|---------|----------|----------|
| 10      | Starter | $5,000   | $60,000  |
| 10      | Growth  | $10,000  | $120,000 |
| 10      | Premium | $20,000  | $240,000 |
| Mix: 5S + 3G + 2P | Mixed | $9,500 | $114,000 |

Plus setup fees: 10 clients x $1,500 = $15,000

Time commitment: ~1 day per week once clients are set up


## Competitive Landscape

### ContentIn.io ($15-48/month)
- Self-service SaaS, user does everything
- Generic AI, no real voice training
- No human review or strategy

### Taplio ($49-149/month)
- Self-service, LinkedIn-focused
- AI ghostwriter, scheduling, analytics
- No done-for-you option

### Our Differentiator
- DONE FOR YOU — client doesn't touch any tech
- Real voice training from a human strategist (not generic AI)
- Greg is a Vistage Speaker — understands sales leadership
- Bundled with LinkedIn profile optimization
- Built on Greg's own proven framework (G Squared Truths model)
- Target market: CEOs, founders, sales leaders in Greg's Vistage network


## Go-To-Market Plan

### Phase 1: Prove It (Days 1-60)
- Greg uses the tool daily for his own LinkedIn
- Post 3x/week consistently
- Track: profile views, connection requests, engagement rate
- Build case study from own results

### Phase 2: Beta Clients (Days 60-90)
- Offer to 2-3 Vistage peers at Starter tier ($500/mo)
- Discounted setup fee ($750) for beta
- Get testimonials and refine the process
- Document time per client

### Phase 3: Launch (Days 90+)
- Full pricing in effect
- Pitch at Vistage meetings
- LinkedIn posts about the service (meta — using the tool to sell the tool)
- Referral incentive: 1 month free for referring a new client


## Technical Setup Per Client

### What Greg Does (one-time, ~4-6 hours)
1. Voice interview (60 min)
2. Build 20-theme bank + 3 example posts
3. Create client config folder with .env, themes.json, examples.txt
4. Set up Dropbox folder for their reference materials
5. Set up Gemini API (uses Greg's API key, billed to Greg — cost ~$5/mo per client)
6. Set up Gmail sending (from Greg's account or client's)
7. LinkedIn OAuth for their account
8. Test run + first week of posts

### Ongoing Per Client (~30 min/week)
1. Run generator (click a button)
2. Quick quality review of 3 options
3. Email to client for approval
4. Post approved content to their LinkedIn

### Client Folder Structure
```
clients/
  client_john_smith/
    .env              (their API keys)
    themes.json       (their 20 truths)
    examples.txt      (their voice samples)
    voice_notes.md    (notes from interview)
```


## Future Considerations

- Web dashboard for clients to approve posts themselves (reduces Greg's time)
- Multi-client management UI
- Analytics dashboard showing engagement growth
- Potential to hire a VA to handle posting once process is documented
- LinkedIn API changes are the biggest risk — monitor quarterly
