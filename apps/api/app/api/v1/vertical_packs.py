"""
Vertical Packs API endpoints: Packs, Versions, Installations, Marketplace.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    VerticalPack, PackVersion, PackInstallation, PackReview, PackCategory, PackEntity
)

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.get("/categories")
async def list_categories(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackCategory
    result = await db.execute(
        select(PackCategory).where(PackCategory.is_active == True).order_by(PackCategory.sort_order)
    )
    categories = result.scalars().all()
    return [
        {"id": c.id, "name": c.name, "slug": c.slug, "description": c.description}
        for c in categories
    ]

@router.post("", status_code=201)
async def create_pack(
    pack_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack
    
    pack = VerticalPack(
        client_id=current_user.client_id,
        category_id=pack_data.get("category_id"),
        name=pack_data.get("name"),
        slug=pack_data.get("slug") or pack_data.get("name", "").lower().replace(" ", "-"),
        description=pack_data.get("description"),
        long_description=pack_data.get("long_description"),
        version=pack_data.get("version", "1.0.0"),
        author_id=current_user.id,
        author_name=pack_data.get("author_name"),
        author_email=pack_data.get("author_email"),
        license=pack_data.get("license", "proprietary"),
        price=pack_data.get("price", 0),
        currency=pack_data.get("currency", "USD"),
        pricing_model=pack_data.get("pricing_model", "one_time"),
        entities=pack_data.get("entities", []),
        workflows=pack_data.get("workflows", []),
        reports=pack_data.get("reports", []),
        dashboards=pack_data.get("dashboards", []),
        templates=pack_data.get("templates", []),
        widgets=pack_data.get("widgets", []),
        segments=pack_data.get("segments", []),
        integrations=pack_data.get("integrations", []),
        custom_roles=pack_data.get("custom_roles", []),
        permissions=pack_data.get("permissions", []),
        dependencies=pack_data.get("dependencies", []),
        install_script=pack_data.get("install_script"),
        uninstall_script=pack_data.get("uninstall_script"),
        post_install_steps=pack_data.get("post_install_steps", []),
        config_schema=pack_data.get("config_schema", {}),
        default_config=pack_data.get("default_config", {}),
        tags=pack_data.get("tags", []),
    )
    db.add(pack)
    await db.commit()
    await db.refresh(pack)
    return {"id": str(pack.id), "message": "Pack created"}

@router.get("")
async def list_packs(
    category_id: Optional[str] = None,
    status: Optional[str] = None,
    is_published: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack
    from sqlalchemy import desc, or_
    
    query = select(VerticalPack).where(VerticalPack.client_id == current_user.client_id)
    
    if category_id:
        query = query.where(VerticalPack.category_id == category_id)
    if status:
        query = query.where(VerticalPack.status == status)
    if is_published is not None:
        query = query.where(VerticalPack.is_published == is_published)
    if is_featured:
        query = query.where(VerticalPack.is_featured == True)
    if search:
        query = query.where(
            or_(VerticalPack.name.ilike(f"%{search}%"), VerticalPack.description.ilike(f"%{search}%"))
        )
    
    query = query.order_by(desc(VerticalPack.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    packs = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "version": p.version,
            "price": float(p.price),
            "currency": p.currency,
            "pricing_model": p.pricing_model,
            "status": p.status,
            "is_published": p.is_published,
            "is_featured": p.is_featured,
            "downloads": p.downloads,
            "rating": float(p.rating),
            "created_at": p.created_at.isoformat(),
        }
        for p in packs
    ]

@router.get("/{pack_id}")
async def get_pack(
    pack_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack
    result = await db.execute(
        select(VerticalPack).where(
            VerticalPack.id == pack_id,
            VerticalPack.client_id == current_user.client_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    return {
        "id": str(pack.id),
        "name": pack.name,
        "slug": pack.slug,
        "description": pack.description,
        "long_description": pack.long_description,
        "version": pack.version,
        "price": float(pack.price),
        "currency": pack.currency,
        "pricing_model": pack.pricing_model,
        "entities": pack.entities,
        "workflows": pack.workflows,
        "reports": pack.reports,
        "dashboards": pack.dashboards,
        "templates": pack.templates,
        "widgets": pack.widgets,
        "segments": pack.segments,
        "integrations": pack.integrations,
        "custom_roles": pack.custom_roles,
        "permissions": pack.permissions,
        "dependencies": pack.dependencies,
        "install_script": pack.install_script,
        "uninstall_script": pack.uninstall_script,
        "post_install_steps": pack.post_install_steps,
        "config_schema": pack.config_schema,
        "default_config": pack.default_config,
        "status": pack.status,
        "is_published": pack.is_published,
        "is_featured": pack.is_featured,
        "downloads": pack.downloads,
        "rating": float(pack.rating),
        "review_count": pack.review_count,
        "tags": pack.tags,
        "created_at": pack.created_at.isoformat(),
        "updated_at": pack.updated_at.isoformat(),
    }

@router.patch("/{pack_id}")
async def update_pack(
    pack_id: str,
    pack_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack
    result = await db.execute(
        select(VerticalPack).where(
            VerticalPack.id == pack_id,
            VerticalPack.client_id == current_user.client_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    for field, value in pack_data.items():
        if hasattr(pack, field):
            setattr(pack, field, value)
    
    pack.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(pack)
    return {"message": "Pack updated"}

@router.delete("/{pack_id}", status_code=204)
async def delete_pack(
    pack_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack
    result = await db.execute(
        select(VerticalPack).where(
            VerticalPack.id == pack_id,
            VerticalPack.client_id == current_user.client_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    await db.delete(pack)
    await db.commit()
    return Response(status_code=204)

@router.post("/{pack_id}/versions", status_code=201)
async def create_pack_version(
    pack_id: str,
    version_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackVersion, VerticalPack
    result = await db.execute(
        select(VerticalPack).where(
            VerticalPack.id == pack_id,
            VerticalPack.client_id == current_user.client_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    version = PackVersion(
        pack_id=pack_id,
        version=version_data.get("version"),
        entities=version_data.get("entities", []),
        workflows=version_data.get("workflows", []),
        reports=version_data.get("reports", []),
        dashboards=version_data.get("dashboards", []),
        templates=version_data.get("templates", []),
        widgets=version_data.get("widgets", []),
        segments=version_data.get("segments", []),
        integrations=version_data.get("integrations", []),
        custom_roles=version_data.get("custom_roles", []),
        permissions=version_data.get("permissions", []),
        dependencies=version_data.get("dependencies", []),
        config_schema=version_data.get("config_schema", {}),
        default_config=version_data.get("default_config", {}),
        install_script=version_data.get("install_script"),
        uninstall_script=version_data.get("uninstall_script"),
        post_install_steps=version_data.get("post_install_steps", []),
        changelog=version_data.get("changelog"),
        breaking_changes=version_data.get("breaking_changes", []),
        migration_notes=version_data.get("migration_notes"),
        release_type=version_data.get("release_type", "patch"),
        is_prerelease=version_data.get("is_prerelease", False),
        release_notes=version_data.get("release_notes"),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return {"id": str(version.id), "message": "Version created"}

@router.get("/{pack_id}/versions")
async def list_pack_versions(
    pack_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackVersion
    result = await db.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id)
        .order_by(desc(PackVersion.created_at))
    )
    versions = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "version": v.version,
            "release_type": v.release_type,
            "is_prerelease": v.is_prerelease,
            "released_at": v.released_at.isoformat() if v.released_at else None,
            "changelog": v.changelog,
        }
        for v in versions
    ]

@router.post("/{pack_id}/install", status_code=201)
async def install_pack(
    pack_id: str,
    install_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import VerticalPack, PackInstallation, PackVersion
    
    result = await db.execute(
        select(VerticalPack).where(
            VerticalPack.id == pack_id,
            VerticalPack.client_id == current_user.client_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    if not pack.is_published:
        raise HTTPException(status_code=400, detail="Pack is not published")
    
    version_id = install_data.get("version_id")
    if version_id:
        version_result = await db.execute(
            select(PackVersion).where(PackVersion.id == version_id, PackVersion.pack_id == pack_id)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
    else:
        version_result = await db.execute(
            select(PackVersion).where(PackVersion.pack_id == pack_id)
            .order_by(desc(PackVersion.created_at)).limit(1)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail="No version available")
    
    installation = PackInstallation(
        pack_id=pack_id,
        version_id=version.id,
        config=install_data.get("config", {}),
        enabled_features=install_data.get("enabled_features", []),
        disabled_features=install_data.get("disabled_features", []),
        custom_config=install_data.get("custom_config", {}),
        installed_by_id=current_user.id,
        installed_version=version.version,
        auto_update=install_data.get("auto_update", True),
        update_channel=install_data.get("update_channel", "stable"),
    )
    
    db.add(installation)
    await db.commit()
    await db.refresh(installation)
    
    pack.downloads += 1
    pack.active_installations += 1
    await db.commit()
    
    return {
        "id": str(installation.id),
        "pack_id": str(pack_id),
        "version": version.version,
        "status": "installing",
        "message": "Pack installation started"
    }

@router.get("/{pack_id}/installations")
async def list_installations(
    pack_id: str,
    status: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackInstallation
    from sqlalchemy import desc
    
    query = select(PackInstallation).where(
        PackInstallation.pack_id == pack_id,
        PackInstallation.client_id == current_user.client_id
    )
    if status:
        query = query.where(PackInstallation.status == status)
    
    result = await db.execute(query.order_by(desc(PackInstallation.installed_at)))
    installations = result.scalars().all()
    
    return [
        {
            "id": str(i.id),
            "pack_id": str(i.pack_id),
            "version": i.installed_version,
            "status": i.status,
            "health_status": i.health_status,
            "installed_at": i.installed_at.isoformat(),
            "auto_update": i.auto_update,
        }
        for i in installations
    ]

@router.post("/{pack_id}/reviews", status_code=201)
async def create_review(
    pack_id: str,
    review_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackReview, VerticalPack, PackInstallation
    
    result = await db.execute(
        select(VerticalPack).where(VerticalPack.id == pack_id)
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    installation_result = await db.execute(
        select(PackInstallation).where(
            PackInstallation.pack_id == pack_id,
            PackInstallation.client_id == current_user.client_id
        )
    )
    installation = installation_result.scalar_one_or_none()
    is_verified_install = installation is not None
    
    review = PackReview(
        pack_id=pack_id,
        user_id=current_user.id,
        installation_id=installation.id if installation else None,
        rating=review_data.get("rating"),
        title=review_data.get("title"),
        content=review_data.get("content"),
        pros=review_data.get("pros", []),
        cons=review_data.get("cons", []),
        is_verified_purchase=True,
        is_verified_installation=is_verified_install,
    )
    
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    # Update pack rating
    from sqlalchemy import func
    rating_result = await db.execute(
        select(func.avg(PackReview.rating)).where(PackReview.pack_id == pack_id)
    )
    avg_rating = rating_result.scalar() or 0
    
    pack_result = await db.execute(select(VerticalPack).where(VerticalPack.id == pack_id))
    pack = pack_result.scalar_one_or_none()
    if pack:
        pack.rating = round(float(avg_rating), 1)
        pack.review_count = (pack.review_count or 0) + 1
        await db.commit()
    
    return {"id": str(review.id), "message": "Review created"}

@router.get("/{pack_id}/reviews")
async def list_reviews(
    pack_id: str,
    rating: Optional[int] = None,
    is_verified: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackReview
    query = select(PackReview).where(PackReview.pack_id == pack_id)
    
    if rating:
        query = query.where(PackReview.rating == rating)
    if is_verified is not None:
        query = query.where(PackReview.is_verified_installation == is_verified)
    
    query = query.order_by(desc(PackReview.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "rating": r.rating,
            "title": r.title,
            "content": r.content,
            "pros": r.pros,
            "cons": r.cons,
            "is_verified_installation": r.is_verified_installation,
            "helpful_count": r.helpful_count,
            "created_at": r.created_at.isoformat(),
            "user_id": str(r.user_id),
        }
        for r in reviews
    ]

@router.post("/{pack_id}/entities", status_code=201)
async def register_pack_entity(
    pack_id: str,
    entity_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackEntity
    
    entity = PackEntity(
        pack_id=pack_id,
        name=entity_data.get("name"),
        slug=entity_data.get("slug") or entity_data.get("name", "").lower().replace(" ", "-"),
        display_name=entity_data.get("display_name"),
        description=entity_data.get("description"),
        category=entity_data.get("category"),
        fields=entity_data.get("fields", []),
        indexes=entity_data.get("indexes", []),
        relationships=entity_data.get("relationships", []),
        list_fields=entity_data.get("list_fields", []),
        detail_fields=entity_data.get("detail_fields", []),
        create_fields=entity_data.get("create_fields", []),
        edit_fields=entity_data.get("edit_fields", []),
        filter_fields=entity_data.get("filter_fields", []),
        sort_fields=entity_data.get("sort_fields", []),
        permissions=entity_data.get("permissions", {}),
        icon=entity_data.get("icon"),
        color=entity_data.get("color"),
        is_system=entity_data.get("is_system", False),
        is_required=entity_data.get("is_required", False),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return {"id": str(entity.id), "message": "Entity registered"}

@router.get("/{pack_id}/entities")
async def list_pack_entities(
    pack_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PackEntity
    result = await db.execute(
        select(PackEntity).where(PackEntity.pack_id == pack_id)
        .order_by(PackEntity.name)
    )
    entities = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "slug": e.slug,
            "display_name": e.display_name,
            "description": e.description,
            "category": e.category,
            "is_system": e.is_system,
            "is_required": e.is_required,
        }
        for e in entities
    ]