<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'categories')]
#[ORM\UniqueConstraint(name: 'uniq_category', columns: ['user_id', 'kind', 'normalized_name'])]
class Category
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: User::class), ORM\JoinColumn(name: 'user_id', nullable: false, onDelete: 'CASCADE')]
    public User $owner;
    #[ORM\Column(length: 10)]
    public string $kind;
    #[ORM\Column(length: 100)]
    public string $name;
    #[ORM\Column(name: 'normalized_name', length: 100)]
    public string $normalizedName;
    #[ORM\Column(type: 'boolean', options: ['default' => false])]
    public bool $archived = false;
}
