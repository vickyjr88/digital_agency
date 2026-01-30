"""
Campaign Content Generation Router
Allows influencers to generate AI content for their accepted campaigns using trends
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from database.config import get_db
from database.models import User, Trend, generate_uuid
from database.marketplace_models import (
    Campaign, CampaignContent, CampaignContentStatus,
    Bid, BidStatusDB, InfluencerProfile, VerificationStatus
)
from auth.dependencies import get_current_user
from auth.decorators import require_user_type
from core.generator import ContentGenerator

router = APIRouter(prefix="/campaign-content", tags=["Campaign Content"])

# ============================================================================
# SCHEMAS
# ============================================================================

class GenerateContentRequest(BaseModel):
    """Request to generate content for a campaign"""
    campaign_id: str = Field(..., description="Campaign to generate content for")
    bid_id: Optional[str] = Field(None, description="Specific bid (if campaign has multiple)")
    trend_id: Optional[str] = Field(None, description="Trend ID to use")
    trend_topic: str = Field(..., min_length=2, description="Trend topic text")
    platform: str = Field(default="instagram", description="Primary platform")
    content_type: str = Field(default="post", description="Content type")

class ContentResponse(BaseModel):
    """Generated content response"""
    id: str
    campaign_id: str
    campaign_title: str
    trend_topic: str
    tweet: Optional[str]
    facebook_post: Optional[str]
    instagram_caption: Optional[str]
    instagram_reel_script: Optional[dict]
    tiktok_idea: Optional[dict]
    linkedin_post: Optional[str]
    platform: str
    content_type: str
    status: str
    generated_at: datetime

class SubmitForApprovalRequest(BaseModel):
    """Request to submit content for brand approval"""
    content_id: str

class BrandFeedbackRequest(BaseModel):
    """Brand feedback on generated content"""
    feedback: str
    approved: bool

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/my-campaigns")
async def get_influencer_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaigns where this influencer has accepted bids (can generate content)."""
    
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found"
        )
    
    if influencer.verification_status != VerificationStatus.APPROVED:
        return {"campaigns": [], "count": 0, "message": "Your influencer profile must be approved to use AI content generation."}
    
    # Get accepted bids for this influencer
    accepted_bids = db.query(Bid).options(
        joinedload(Bid.campaign).joinedload(Campaign.brand_entity)
    ).filter(
        Bid.influencer_id == influencer.id,
        Bid.status == BidStatusDB.ACCEPTED
    ).all()
    
    campaigns_data = []
    for bid in accepted_bids:
        campaign = bid.campaign
        campaigns_data.append({
            "id": campaign.id,
            "bid_id": bid.id,
            "title": campaign.title,
            "description": campaign.description,
            "brand": {
                "id": campaign.brand_entity.id if campaign.brand_entity else None,
                "name": campaign.brand_entity.name if campaign.brand_entity else "Brand"
            },
            "platforms": campaign.platforms or [],
            "content_types": campaign.content_types or [],
            "voice": campaign.voice,
            "hashtags": campaign.hashtags or [],
            "key_messages": campaign.key_messages or [],
            "target_audience": campaign.target_audience,
            "content_style": campaign.content_style,
            "product_name": campaign.product_name,
            "product_description": campaign.product_description,
            "deadline": campaign.deadline.isoformat() if campaign.deadline else None,
            "bid_amount": bid.amount,
            "content_count": len(campaign.generated_contents) if campaign.generated_contents else 0
        })
    
    return {
        "campaigns": campaigns_data,
        "count": len(campaigns_data)
    }


@router.get("/trends")
async def get_available_trends(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent trends that can be used for content generation."""
    
    trends = db.query(Trend).order_by(Trend.timestamp.desc()).limit(limit).all()
    
    return {
        "trends": [
            {
                "id": t.id,
                "topic": t.topic,
                "volume": t.volume,
                "source": t.source,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            }
            for t in trends
        ]
    }


@router.post("/generate")
async def generate_campaign_content(
    request: GenerateContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI content for a campaign using a trend."""
    
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found. Complete onboarding first."
        )
    
    if influencer.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your influencer profile must be approved to generate content."
        )
    
    # Get campaign
    campaign = db.query(Campaign).options(
        joinedload(Campaign.brand_entity)
    ).filter(Campaign.id == request.campaign_id).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Verify influencer has an accepted bid for this campaign
    accepted_bid = db.query(Bid).filter(
        Bid.campaign_id == campaign.id,
        Bid.influencer_id == influencer.id,
        Bid.status == BidStatusDB.ACCEPTED
    ).first()
    
    if not accepted_bid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have an accepted bid for this campaign"
        )
    
    # Get trend info if ID provided
    trend = None
    if request.trend_id:
        trend = db.query(Trend).filter(Trend.id == request.trend_id).first()
    
    # Build persona from campaign data
    brand_name = campaign.brand_entity.name if campaign.brand_entity else "Brand"
    persona = {
        "name": campaign.product_name or campaign.title or brand_name,
        "role": campaign.brand_entity.industry if campaign.brand_entity else "Brand",
        "voice": campaign.voice or "Professional and engaging",
        "content_focus": campaign.content_themes or campaign.content_types or ["engagement"],
        "key_message": campaign.key_messages[0] if campaign.key_messages else campaign.description,
        "sample_tone": campaign.sample_tone,
        "hashtags": campaign.hashtags or [],
        "target_audience": campaign.target_audience,
        "content_style": campaign.content_style,
        "product_description": campaign.product_description,
        "dos": campaign.content_dos or [],
        "donts": campaign.content_donts or []
    }
    
    # Build enhanced prompt
    prompt = _build_campaign_prompt(
        trend_topic=request.trend_topic,
        persona=persona,
        platform=request.platform,
        content_type=request.content_type,
        campaign=campaign
    )
    
    # Generate content
    try:
        generator = ContentGenerator()
        
        # Use custom generation for campaigns
        content_data = generator.generate_content(request.trend_topic, persona)
        
        if not content_data:
            raise Exception("Content generation returned empty")
        
        model_used = "gemini-2.0-flash"  # Default model
        
    except Exception as e:
        logging.error(f"Content generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}"
        )
    
    # Save generated content
    campaign_content = CampaignContent(
        campaign_id=campaign.id,
        bid_id=accepted_bid.id,
        influencer_id=influencer.id,
        trend_id=request.trend_id,
        trend_topic=request.trend_topic,
        tweet=content_data.get("tweet"),
        facebook_post=content_data.get("facebook_post"),
        instagram_caption=content_data.get("instagram_caption") or content_data.get("facebook_post"),
        instagram_reel_script=content_data.get("instagram_reel_script"),
        tiktok_idea=content_data.get("tiktok_idea"),
        linkedin_post=content_data.get("linkedin_post"),
        platform=request.platform,
        content_type=request.content_type,
        prompt_used=prompt,
        model_used=model_used,
        status=CampaignContentStatus.DRAFT
    )
    
    db.add(campaign_content)
    db.commit()
    db.refresh(campaign_content)
    
    return {
        "message": "Content generated successfully",
        "content": {
            "id": campaign_content.id,
            "campaign_id": campaign.id,
            "campaign_title": campaign.title,
            "trend_topic": request.trend_topic,
            "tweet": campaign_content.tweet,
            "facebook_post": campaign_content.facebook_post,
            "instagram_caption": campaign_content.instagram_caption,
            "instagram_reel_script": campaign_content.instagram_reel_script,
            "tiktok_idea": campaign_content.tiktok_idea,
            "linkedin_post": campaign_content.linkedin_post,
            "platform": campaign_content.platform,
            "content_type": campaign_content.content_type,
            "status": campaign_content.status.value,
            "generated_at": campaign_content.generated_at.isoformat()
        }
    }


@router.get("/my-content")
async def get_my_generated_content(
    campaign_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get content generated by this influencer."""
    
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        return {"contents": [], "count": 0}
    
    query = db.query(CampaignContent).options(
        joinedload(CampaignContent.campaign)
    ).filter(
        CampaignContent.influencer_id == influencer.id
    )
    
    if campaign_id:
        query = query.filter(CampaignContent.campaign_id == campaign_id)
    
    if status_filter:
        try:
            status_enum = CampaignContentStatus(status_filter)
            query = query.filter(CampaignContent.status == status_enum)
        except:
            pass
    
    total = query.count()
    offset = (page - 1) * limit
    contents = query.order_by(CampaignContent.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "contents": [
            {
                "id": c.id,
                "campaign_id": c.campaign_id,
                "campaign_title": c.campaign.title if c.campaign else None,
                "trend_topic": c.trend_topic,
                "tweet": c.tweet,
                "instagram_caption": c.instagram_caption,
                "platform": c.platform,
                "content_type": c.content_type,
                "status": c.status.value,
                "brand_feedback": c.brand_feedback,
                "generated_at": c.generated_at.isoformat() if c.generated_at else None,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                "approved_at": c.approved_at.isoformat() if c.approved_at else None
            }
            for c in contents
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{content_id}")
async def get_content_detail(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed view of generated content."""
    
    content = db.query(CampaignContent).options(
        joinedload(CampaignContent.campaign).joinedload(Campaign.brand_entity),
        joinedload(CampaignContent.influencer)
    ).filter(CampaignContent.id == content_id).first()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check access - influencer who created it OR brand owner
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    is_influencer_owner = influencer and content.influencer_id == influencer.id
    is_brand_owner = content.campaign.brand_id == current_user.id
    
    if not is_influencer_owner and not is_brand_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this content"
        )
    
    return {
        "id": content.id,
        "campaign": {
            "id": content.campaign.id,
            "title": content.campaign.title,
            "brand_name": content.campaign.brand_entity.name if content.campaign.brand_entity else None
        },
        "trend_topic": content.trend_topic,
        "tweet": content.tweet,
        "facebook_post": content.facebook_post,
        "instagram_caption": content.instagram_caption,
        "instagram_reel_script": content.instagram_reel_script,
        "tiktok_idea": content.tiktok_idea,
        "linkedin_post": content.linkedin_post,
        "platform": content.platform,
        "content_type": content.content_type,
        "status": content.status.value,
        "brand_feedback": content.brand_feedback,
        "revision_notes": content.revision_notes,
        "generated_at": content.generated_at.isoformat() if content.generated_at else None,
        "submitted_at": content.submitted_at.isoformat() if content.submitted_at else None,
        "approved_at": content.approved_at.isoformat() if content.approved_at else None,
        "is_owner": is_influencer_owner,
        "is_brand": is_brand_owner
    }


@router.post("/{content_id}/submit")
async def submit_for_approval(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit generated content for brand approval."""
    
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Influencer profile required"
        )
    
    content = db.query(CampaignContent).filter(
        CampaignContent.id == content_id,
        CampaignContent.influencer_id == influencer.id
    ).first()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found or not yours"
        )
    
    if content.status != CampaignContentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content is already {content.status.value}"
        )
    
    content.status = CampaignContentStatus.PENDING_APPROVAL
    content.submitted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Content submitted for brand approval", "status": "pending_approval"}


@router.post("/{content_id}/approve")
async def approve_content(
    content_id: str,
    feedback: Optional[BrandFeedbackRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Brand approves or requests revision on content."""
    
    content = db.query(CampaignContent).options(
        joinedload(CampaignContent.campaign)
    ).filter(CampaignContent.id == content_id).first()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Verify brand ownership
    if content.campaign.brand_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign owner can approve content"
        )
    
    if content.status != CampaignContentStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content is not pending approval (status: {content.status.value})"
        )
    
    if feedback:
        content.brand_feedback = feedback.feedback
        if feedback.approved:
            content.status = CampaignContentStatus.APPROVED
            content.approved_at = datetime.utcnow()
        else:
            content.status = CampaignContentStatus.REJECTED
            content.revision_notes = feedback.feedback
    else:
        content.status = CampaignContentStatus.APPROVED
        content.approved_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Content {'approved' if content.status == CampaignContentStatus.APPROVED else 'rejected'}",
        "status": content.status.value
    }


@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete draft content."""
    
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    content = db.query(CampaignContent).filter(
        CampaignContent.id == content_id
    ).first()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Only allow deletion of drafts by the influencer who created it
    if not influencer or content.influencer_id != influencer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own content"
        )
    
    if content.status != CampaignContentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft content can be deleted"
        )
    
    db.delete(content)
    db.commit()
    
    return {"message": "Content deleted"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_campaign_prompt(
    trend_topic: str,
    persona: dict,
    platform: str,
    content_type: str,
    campaign: Campaign
) -> str:
    """Build enhanced prompt for campaign content generation."""
    
    dos_text = "\n".join([f"- {d}" for d in persona.get("dos", [])]) or "None specified"
    donts_text = "\n".join([f"- {d}" for d in persona.get("donts", [])]) or "None specified"
    
    return f"""
    You are creating social media content for a brand campaign.
    
    **Brand/Product:**
    - Name: {persona['name']}
    - Industry: {persona['role']}
    - Voice/Tone: {persona['voice']}
    - Target Audience: {persona.get('target_audience') or 'General audience'}
    - Content Style: {persona.get('content_style') or 'Engaging'}
    
    **Product Details:**
    {persona.get('product_description') or 'See campaign brief'}
    
    **Key Messages:**
    {', '.join(persona.get('content_focus', [])) if persona.get('content_focus') else 'Engage audience'}
    
    **Sample Tone (if provided):**
    {persona.get('sample_tone') or 'Match the brand voice above'}
    
    **Hashtags to use:**
    {', '.join(persona.get('hashtags', [])) if persona.get('hashtags') else 'Use relevant trending hashtags'}
    
    **Content Do's:**
    {dos_text}
    
    **Content Don'ts:**
    {donts_text}
    
    **Task:**
    Create content for {platform} ({content_type}) based on the trending topic: "{trend_topic}"
    The content must naturally bridge the trend to the brand's product/identity.
    
    **Required Outputs (JSON format):**
    1. "tweet": A short, engaging tweet (max 280 chars) with hashtags.
    2. "facebook_post": A slightly longer post suitable for Facebook.
    3. "instagram_caption": Caption for Instagram post with hashtags.
    4. "instagram_reel_script": A script for a 15-30s Reel (Visuals + Audio + Caption).
    5. "tiktok_idea": A concept for a TikTok video (Hook + Action + Sound).
    6. "linkedin_post": Professional version for LinkedIn (optional).
    
    **Output Format:**
    Provide ONLY the JSON object. Do not add any markdown formatting or extra text.
    {{
        "tweet": "...",
        "facebook_post": "...",
        "instagram_caption": "...",
        "instagram_reel_script": {{"visuals": "...", "audio": "...", "caption": "..."}},
        "tiktok_idea": {{"hook": "...", "action": "...", "sound": "..."}},
        "linkedin_post": "..."
    }}
    """
