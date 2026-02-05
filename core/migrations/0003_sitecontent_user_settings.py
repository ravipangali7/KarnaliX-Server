# Generated manually: SiteContent model and User.settings field

from django.db import migrations, models


def seed_site_content(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    default_hero = {
        "title": "Play. Win. Repeat.",
        "subtitle": "Experience the thrill of 500+ games with live dealers, instant payouts, and unbeatable odds. Join thousands of winners today!",
        "ctaText": "Start Playing",
        "ctaHref": "/signup",
        "badge": "Nepal's #1 Gaming Platform",
    }
    default_promos = [
        {"id": "welcome", "variant": "welcome", "badge": "LIMITED OFFER", "title": "Welcome Bonus", "highlight": "200%", "subtitle": "Up to ₹50,000", "description": "Double your first deposit and start winning big!", "cta": "Claim Now", "href": "/signup"},
        {"id": "referral", "variant": "referral", "badge": "REFER & EARN", "title": "Invite Friends", "highlight": "₹500", "subtitle": "Per Referral", "description": "Share your link and earn for every friend who joins!", "cta": "Get Your Link", "href": "/affiliate"},
        {"id": "tournament", "variant": "tournament", "badge": "WEEKLY EVENT", "title": "Mega Tournament", "highlight": "₹10 Lakh", "subtitle": "Prize Pool", "description": "Compete with the best and win massive rewards!", "cta": "Join Now", "href": "/tournaments"},
        {"id": "cashback", "variant": "cashback", "badge": "EVERY WEEK", "title": "Cashback Offer", "highlight": "15%", "subtitle": "Weekly Cashback", "description": "Get money back on your losses every week!", "cta": "Learn More", "href": "/promotions"},
    ]
    default_testimonials = [
        {"id": 1, "name": "Rajesh K.", "avatar": "RK", "location": "Kathmandu", "game": "Aviator", "amount": "₹2,50,000", "message": "Won big on Aviator! The platform is super smooth and withdrawals are instant. Best gaming site in Nepal!", "rating": 5},
        {"id": 2, "name": "Priya S.", "avatar": "PS", "location": "Pokhara", "game": "Teen Patti", "amount": "₹1,80,000", "message": "Love playing Teen Patti here. The live dealers are professional and the experience is amazing!", "rating": 5},
        {"id": 3, "name": "Amit G.", "avatar": "AG", "location": "Biratnagar", "game": "Cricket Betting", "amount": "₹5,00,000", "message": "IPL betting made me rich! Best odds I've found anywhere. Customer support is also very helpful.", "rating": 5},
        {"id": 4, "name": "Sita M.", "avatar": "SM", "location": "Lalitpur", "game": "Rummy", "amount": "₹95,000", "message": "Daily tournaments with great prizes. I've been playing here for 6 months and never had any issues.", "rating": 4},
    ]
    default_recent_wins = [
        {"user": "Ra***sh", "game": "Aviator", "amount": "₹45,000", "time": "2 min ago"},
        {"user": "Pr***ya", "game": "Lightning Roulette", "amount": "₹1,20,000", "time": "5 min ago"},
        {"user": "Am***it", "game": "Teen Patti", "amount": "₹28,000", "time": "8 min ago"},
        {"user": "Su***sh", "game": "Sweet Bonanza", "amount": "₹65,000", "time": "12 min ago"},
        {"user": "An***ta", "game": "Blackjack", "amount": "₹2,50,000", "time": "15 min ago"},
        {"user": "Bi***al", "game": "Crazy Time", "amount": "₹85,000", "time": "18 min ago"},
    ]
    default_coming_soon = [
        {"id": "poker-tournament", "name": "World Poker Championship", "image": "https://images.unsplash.com/photo-1609743522653-52354461eb27?w=400&h=300&fit=crop", "launchDate": "Coming Feb 2024", "description": "The biggest online poker tournament with ₹1 Crore prize pool"},
        {"id": "cricket-fantasy", "name": "Fantasy Cricket Pro", "image": "https://images.unsplash.com/photo-1531415074968-036ba1b575da?w=400&h=300&fit=crop", "launchDate": "Coming March 2024", "description": "Build your dream team and win real cash prizes"},
        {"id": "slot-megaways", "name": "Megaways Jackpot", "image": "https://images.unsplash.com/photo-1606167668584-78701c57f13d?w=400&h=300&fit=crop", "launchDate": "Coming Soon", "description": "117,649 ways to win massive jackpots"},
        {"id": "live-teenpatti-vip", "name": "VIP Teen Patti Lounge", "image": "https://images.unsplash.com/photo-1511193311914-0346f16efe90?w=400&h=300&fit=crop", "launchDate": "Coming March 2024", "description": "Exclusive high-stakes tables with professional dealers"},
        {"id": "horse-racing", "name": "Virtual Horse Racing", "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=300&fit=crop", "launchDate": "Coming April 2024", "description": "Realistic horse racing simulations with live betting"},
    ]
    keys_data = [
        ("hero", default_hero),
        ("promos", default_promos),
        ("testimonials", default_testimonials),
        ("recent_wins", default_recent_wins),
        ("coming_soon", default_coming_soon),
    ]
    for key, data in keys_data:
        SiteContent.objects.get_or_create(key=key, defaults={"data": data})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_kyc_rejection_remarks'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='settings',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name='SiteContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=50, unique=True)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Site Content',
                'verbose_name_plural': 'Site Content',
                'ordering': ['key'],
            },
        ),
        migrations.RunPython(seed_site_content, noop),
    ]
