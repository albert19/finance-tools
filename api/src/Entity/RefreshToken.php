<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'refresh_tokens')]
#[ORM\UniqueConstraint(name: 'token_hash', columns: ['token_hash'])]
#[ORM\Index(name: 'idx_refresh_family', columns: ['family_id'])]
#[ORM\Index(name: 'idx_refresh_user', columns: ['user_id'])]
class RefreshToken
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: User::class), ORM\JoinColumn(name: 'user_id', nullable: false, onDelete: 'CASCADE')]
    public User $owner;
    #[ORM\Column(name: 'family_id', length: 36, options: ['fixed' => true])]
    public string $familyId;
    #[ORM\Column(name: 'token_hash', length: 64, options: ['fixed' => true])]
    public string $tokenHash;
    #[ORM\Column(name: 'expires_at', type: 'datetime_immutable')]
    public \DateTimeImmutable $expiresAt;
    #[ORM\Column(name: 'consumed_at', type: 'datetime_immutable', nullable: true)]
    public ?\DateTimeImmutable $consumedAt = null;
    #[ORM\Column(name: 'revoked_at', type: 'datetime_immutable', nullable: true)]
    public ?\DateTimeImmutable $revokedAt = null;
}
